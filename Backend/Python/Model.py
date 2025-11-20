# -------------------------------------------------------
# 🔵 IMPORTS & ENVIRONMENT SETUP
# -------------------------------------------------------
# Load required libraries, environment variables (.env),
# weather / email tools, and API keys.

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
import requests
from typing import Literal
import os
from dotenv import load_dotenv
import json
from Tools.WeatherTool import WeatherTool
# from Tools.MailTool import MailTool
from Tools.Ooth2MailTool import MailToolOAuth
from datetime import datetime

load_dotenv()
api_key = os.getenv("LLM_API_KEY")
node_port = os.getenv("NODE_PORT")

# -------------------------------------------------------
# 🔵 REQUEST TYPE SCHEMA (for routing decisions)
# -------------------------------------------------------
# Defines how the router LLM responds:
# - request_type: tool_call or direct_model_response
# - confidence_score: how certain the model is
# - description: cleaned user intent
# -------------------------------------------------------
class RequestType(BaseModel):
    """Router LLM call: Determine the type of request"""

    request_type: Literal["tool_call", "direct_model_response"] = Field(
        description=(
            "Classify the user's request into one of two MODES:\n\n"
            "1. tool_call → Use this when the assistant needs external tools, structured data, "
            "database access, context gathering, or multi-step reasoning. This also includes any request "
            "that requires knowledge of the assistant's own tools, abilities, or features. "
            "For example:\n"
            "   - 'What can you do?'\n"
            "   - 'Show me your capabilities'\n"
            "   - Requests that may involve sending emails, fetching weather, or using any other tool.\n"
            "In short, ANY request that requires reasoning about tools, functions, or external resources "
            "falls under this mode.\n\n"
            "2. direct_model_response → Pure conversational mode. The assistant should respond directly without "
            "tools. This includes greetings, opinions, jokes, cultural explanations, emotional support, "
            "or simple factual questions that can be answered without reasoning about or invoking tools."
        )
    )                
           
    confidence_score: float = Field(description="Confidence score between 0 and 1, describing how sure the model is with his routing decision")
    description: str = Field(description="Cleaned description of the request")


# -------------------------------------------------------
# 🔵 MODEL CLASS INITIALIZATION
# -------------------------------------------------------
# Creates:
# - Gemini client
# - Tool schemas (weather + email tools)
# - Tool configuration passed to Gemini
# - In-memory message history
# -------------------------------------------------------
class Model:
    if not api_key:
        raise ValueError("Missing LLM_API_KEY. Did you forget to set it in your .env file?")
    def __init__(self):
        self.LLMmodel = genai.Client(api_key=api_key)
        self.messages = []
        # -------------------------------------------------------
        # 🔵 WEATHER TOOL DECLARATION
        # -------------------------------------------------------
        # Schema describing the weather_request tool.
        # Gemini uses this to understand function parameters.
        # Dummy arg is required by the API but ignored.
        # -------------------------------------------------------
        weather_request = {
            "name": "weather_request",
            "description": (
                "Fetches the weather forecast (current, hourly, or daily) for a specified city or location. "
                "The user input may or may not explicitly mention the forecast type or location. "
                "If no forecast type is mentioned, default to 'current'. If no city is mentioned, default to a fallback location. "
                "The function automatically handles geocoding if a city name is present in the input."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "dummy": { 
                        # Placeholder field
                        "type": "boolean",
                        "description": "This is a placeholder and should be ignored"
                    },
                },
                # "required": [],
            },
        }

        # -------------------------------------------------------
        # 🔵 EMAIL TOOL DECLARATION
        # -------------------------------------------------------
        # Supports:
        # - Send email
        # - Read email
        # Gemini extracts:
        # - to_email
        # - subject
        # - body
        # No need for the user to repeat them.
        # -------------------------------------------------------
        email_requests  = {
            "name": "email_requests",
            "description": (
                "Performs various email operations: send, read.\n\n"
                "The 'send' functionality allows the assistant to send an email using the inputs provided "
                "by the user, including the recipient (to_email), subject, and body.\n\n"
                "You do not need to ask the user to re-enter this information — it will be passed to the function directly. "
                "Proceed to extract these values and call the function accordingly."
                "note this feature needs authentication first. so tell the user to authenticate if not done yet."
            ),
            "parameters": {
              "type": "object",
              "properties": {
                "functionality": {
                  "type": "string",
                  "enum": ["send", "read"] # "delete", "search"
                },
                "num_of_mails": { 
                    "type": "integer",
                    "description": "The number of emails the user wants to retrieve. Defaults to 10 if not provided."
                },
                "to_email": {
                    "type": "string",
                    "description": "The recipient’s email address extracted from the user's message."
                },
                "subject": {
                    "type": "string",
                    "description": (
                        "The subject line of the email. If not explicitly stated by the user, "
                        "infer an appropriate subject based on the context of the message."
                    )
                },
                "body": {
                    "type": "string",
                    "description": (
                        "The main content of the email. This may not always be explicitly mentioned — for example, "
                        "the user might say: 'Send a congratulations mail to example@example.com for his graduation'. "
                        "In such cases, infer the full body and format it clearly, using appropriate spacing and line breaks."
                    )
                }
              },
              "required": ["functionality"]
            }
        }

# -------------------------------------------------------
# 🔵 Gemini TOOLS CONFIGURATION
# -------------------------------------------------------
# Combine weather_request + email_requests into a single
# tool object that Gemini can call.
# -------------------------------------------------------
        self.tools = types.Tool(
            function_declarations=[
                weather_request,
                email_requests
            ]
        )
        self.config = types.GenerateContentConfig(tools=[self.tools])

# -------------------------------------------------------
# 🔵 SAVE CHAT HISTORY TO NODE SERVER
# -------------------------------------------------------
# Sends the last N messages (except system prompt)
# to your Node backend for persistent storage.
# -------------------------------------------------------
    def save_history(self,Bearer_TOKEN):
        url = f"http://localhost:{node_port}/api/v1/fastapi/save-chat-history" 
        headers = {
            "Content-Type": "application/json",
            "Authorization": Bearer_TOKEN
        }
        #⚠️⚠️ could be further modified if needed in terms of time complixity
        payload = {
            "history": [
                {
                    "role": msg.role,
                    "content": "".join([part.text for part in msg.parts])  # flatten parts into a string
                }
                for msg in self.messages[1:]  # skip the first message
            ]
        }
        response = requests.post(url, data=json.dumps(payload) , headers=headers)
        return response.status_code   


# -------------------------------------------------------
# 🔵 INITIALIZE USER HISTORY
# -------------------------------------------------------
# Fetches past conversation history from Node backend.
# Rebuilds the message list:
# - Adds system instructions (location, time, persona)
# - Loads historical messages if available
# -------------------------------------------------------
    def init_user_history(self,location,current_datetime,Bearer_TOKEN):

        url = f"http://localhost:{node_port}/api/v1/fastapi/user-data"  
        # Optional headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": Bearer_TOKEN
        }
        response = requests.get(url,headers=headers)  #headers=headers, data=json.dumps(payload)
        if response.status_code == 200 :
            print("fetched user history successfully")
            temp = response.json()
            data = temp['data']['user']
            chatHistory = data.get("chatHistory", [])
            # medicalHistory = data.get("medicalHistory", [])
            # If you want dynamic location/time each request, consider inserting SYSTEM_INSTRUCTION every request, or always append a "system/user context" message first.
            SYSTEM_INSTRUCTION =(
                                    f"Your name is ZakAi and you are a daily personal assistant. Forget about being an llm trained by google. The user’s location is: {location}, current time is: {current_datetime}"
                                    f"Use this location, date, and time to improve the accuracy, relevance, and personalization of your responses. "
                                    f"If the user's request benefits from local context (e.g. suggestions, history, culture, language, events), "
                                    f"adapt the answer accordingly. Only skip using location if it’s clearly unrelated to the query."
                                    f"Note: Do not include or mention the user's location in your response unless the user explicitly asks for it."
                                )
            # ⚠️⚠️ make sure system prompt should me model or user role according to gemini docs
            self.messages = [
                types.Content(role="model", parts=[types.Part.from_text(text=SYSTEM_INSTRUCTION)])
            ]
            for message in chatHistory:
                self.add_message(message["role"], message["content"])
        else:
            print(f"❌ Error fetching user history: {response.status_code}")
            SYSTEM_INSTRUCTION =(
                                    f"Your name is ZakAi and you are a daily personal assistant. Forget about being an llm trained by google. The user’s location is: {location}, current time is: {current_datetime}"
                                    f"Use this location, date, and time to improve the accuracy, relevance, and personalization of your responses. "
                                    f"If the user's request benefits from local context (e.g. suggestions, history, culture, language, events), "
                                    f"adapt the answer accordingly. Only skip using location if it’s clearly unrelated to the query."
                                    f"Note: Do not include or mention the user's location in your response unless the user explicitly asks for it."
                                )
            self.messages = [
                types.Content(role="user", parts=[types.Part.from_text(text=SYSTEM_INSTRUCTION)])
            ]

# -------------------------------------------------------
# 🔵 ADD MESSAGE TO MEMORY WITH TRIMMING
# -------------------------------------------------------
# Appends new messages and trims old ones
# while always keeping the system message intact.
# Future: you can add summarization instead of trimming.
# -------------------------------------------------------
    def add_message(self, role, content, max_history=50):
        self.messages.append(
            types.Content(role=role, parts=[types.Part.from_text(text=content)])
        )
        # Keep the first message (system) and trim the rest if needed
        # ⚠️⚠️ summary messages could be added here instead of removing old messages
        if len(self.messages) > max_history:
            print("trimming history")
            self.messages.pop(1)  # remove oldest
            print(f"make sure system prompt is still there: {self.messages[0]}")

# -------------------------------------------------------
# 🔵 TOOL CALL EXECUTION (Weather / Email)
# -------------------------------------------------------
# 1) Gemini decides a tool should be used
# 2) Extract function_call + args
# 3) Run the corresponding Python implementation:
#    - WeatherTool → get_weather_response()
#    - MailTool    → fetch_unread_emails(), send_email_tool()
# -------------------------------------------------------
    def tool_call(self,userInput,current_datetime,lat,lon,Bearer_TOKEN):
        try:
            response = self.LLMmodel.models.generate_content(
                model="gemini-2.5-flash",
                contents = self.messages,
                config=self.config
            )
            # print(f"⚠️💔 debugging",response)
            if not response.candidates[0].content.parts[0].function_call:
                raise ValueError("Tool call predicted but not present in model response")

            def call_function(name, args, Bearer_TOKEN):

                # -------------------------------------------------------
                # 🔵 WEATHER TOOL EXECUTION
                # -------------------------------------------------------
                if name.lower() == "weather_request" :
                    weatherTool_instance = WeatherTool()
                    return weatherTool_instance.get_weather_response(userInput,current_datetime,lat,lon)
                
                # -------------------------------------------------------
                # 🔵 EMAIL TOOL EXECUTION
                # -------------------------------------------------------
                # ⚠️⚠️ repeated GET request 
                elif name.lower() == "email_requests":
                    url = f"http://localhost:{node_port}/api/v1/fastapi/getUserAuthDetails"  
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": Bearer_TOKEN
                    }
                    response = requests.get(url,headers=headers)  #headers=headers, data=json.dumps(payload)

                    if response.status_code == 200 :
                        print(f"fetched user email auth successfully")
                        temp = response.json()
                        is_authenticated = temp['data']['is_authenticated']
                        email = temp['data']['email']
                        access_token = temp['data']['access_token']
                        refresh_token = temp['data']['refresh_token']
                        access_token_expiry = temp['data']['access_token_expiry']
                        
                        if not is_authenticated:
                            url = f"http://127.0.0.1:8000/auth"  
                            return f"❌ You need to authenticate your email account first. Please visit the {url} to authorize."
                        else:
                            response = requests.get(url,headers=headers)  # ❌ WHY CALL AGAIN?! #headers=headers, data=json.dumps(payload) 
                            functionality=args.get("functionality")
             
                            MailTool_instance = MailToolOAuth(access_token,refresh_token,access_token_expiry,Bearer_TOKEN)
                            if functionality=="read" :
                                num_of_mails=int(args.get("num_of_mails", 10))
                                return MailTool_instance.fetch_unread_emails(num_of_mails)
                            elif functionality == "send":
                                sender_email = email
                                to_email=args.get("to_email")
                                subject=args.get("subject")
                                body=args.get("body")
                                return MailTool_instance.send_email(sender_email,to_email,subject,body) #userInput
                    else:
                        print(f"❌ Error fetching user email auth status: {response.status_code}")
                        return "❌ Error fetching user email auth status."
                    
                # if name == "search_DB":
                #     return Retrieval.search_db()

            if response.candidates[0].content.parts[0].function_call:
                function_call = response.candidates[0].content.parts[0].function_call
                name = function_call.name
                args = function_call.args
                result = call_function(name,args,Bearer_TOKEN)
                self.messages.append(types.Content(role="model", parts=[types.Part.from_text(text=result)]))
                reply = result
                return reply
        # -------------------------------------------------------
        # 🔵 TOOL CALL FALLBACK
        # -------------------------------------------------------
        except Exception as e:
            print(f"[Fallback Triggered]: {e}")
            try:
                # Take the raw tool_call fallback text
                fallback_text = response.candidates[0].content.parts[0].text
                # Prepare a rephrase instruction for the LLM
                rephrase_prompt = (
                    f"The following response was generated as a fallback from a tool call:\n\n{fallback_text}\n\n"
                    f"Your task: Either improve and rephrase this message to sound natural, conversational, and helpful, "
                    f"OR if you are able to answer the user's query more accurately yourself, do so instead of just rephrasing. "
                    f"Make sure the response is friendly and clear."
                )
                # Add the rephrase instruction as user message
                self.messages.append(
                    types.Content(role="user", parts=[types.Part.from_text(text=rephrase_prompt)])
                )
                # Generate a more natural reply using the LLM
                response = self.LLMmodel.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=self.messages,
                )
                reply = response.text
                # Save the model's refined reply in memory
                self.messages.append(types.Content(role="model", parts=[types.Part.from_text(text=reply)]))
                return reply 
            except Exception as e:
                print(f"❌ Error in fallback response: {e}")
                return self.direct_model_response()


# -------------------------------------------------------
# 🔵 DIRECT MODEL RESPONSE (Chat instead of Tools)
# -------------------------------------------------------
# Handles normal conversation:
# greetings, explanations, opinions, cultural info, etc.
# No function calls are attempted.
# -------------------------------------------------------
    def direct_model_response(self):
        response = self.LLMmodel.models.generate_content(
            model="gemini-2.5-flash",
            contents = self.messages,
        )
        reply = response.text
        self.messages.append(types.Content(role="model", parts=[types.Part.from_text(text=reply)]))
        return reply

# -------------------------------------------------------
# 🔵 ROUTER LLM CALL
# -------------------------------------------------------
# Sends entire conversation to Gemini with a JSON schema.
# Gemini classifies input:
#   → "tool_call"
#   → "direct_model_response"
# Based on the classification, the message is routed.
# -------------------------------------------------------

    def route_request(self,user_input: str,current_datetime,lat,lon,Bearer_TOKEN):
        """Router LLM call to determine the type of request, and route it to start execution"""
        print(f"in Router:")
        # ❌ router shouldn't see the whole history to avoid hullucinations
        temp = []
        temp.append(types.Content(role="user", parts=[types.Part.from_text(text=user_input)]))
        response = self.LLMmodel.models.generate_content(
            model="gemini-2.5-flash",
            contents = self.messages,
            config={
                # "system_instruction"=SYSTEM_INSTRUCTION
                "response_mime_type": "application/json",
                "response_schema": RequestType,
            }
        )
        result = json.loads(response.text)
        print(f"result "+str(result))
        request_type = result.get("request_type")
        description = result.get("description", "No description provided")
        confidence_score = result.get("confidence_score")
        print(f"[Routing Decision]: {request_type} | Confidence: {confidence_score}")

        if(request_type=="tool_call"):
            reply = self.tool_call(user_input,current_datetime,lat,lon,Bearer_TOKEN)
        # elif(request_type=="rag_response"):
        #     reply = self.RAG_Response(user_input)   
        else:
            reply = self.direct_model_response()
        
        return reply

# -------------------------------------------------------
# 🔵 MAIN ENTRY POINT: generate_response()
# -------------------------------------------------------
# Steps:
# 1. Insert user message into memory
# 2. Call router → routing decision
# 3. Execute tool_call OR direct reply
# 4. Return final output
# -------------------------------------------------------   
    def generate_response(self, user_message,location,Bearer_TOKEN):
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # if not self.messages:
            #     print("initializing user history")
            #     self.init_user_history(location,current_datetime,Bearer_TOKEN)
            try:
                self.messages.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))
                result = self.route_request(user_message,current_datetime,location.get("latitude"),location.get("longitude"),Bearer_TOKEN)
                return result
            except Exception as e:
                print(f"❌error:",e)
                return "error, please try again"

# user_message = input("enter you request: ")
# location = { "latitude": 29.9866, "longitude": 31.4406 }            
# print(Model().generate_response(user_message,location))