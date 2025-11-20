from google import genai
from google.genai import types
# from google.generativeai.types import FunctionDeclaration, Tool
import requests
import os
from dotenv import load_dotenv
from typing import Literal, Dict
from pydantic import BaseModel, Field
import json


class WeatherRequestSchema(BaseModel):
    """
        Unified classification schema for weather-related user requests.
        
        This schema asks the model to perform a dual task:
        1. Determine whether the user's request includes a city name that needs to be geocoded.
        2. Classify the user's intent into one of three weather forecast types: 'current', 'hourly', or 'daily'.

        Instructions to model:
        - If no city name is mentioned, set `has_city` to False and leave `city_name` and `country` as empty strings.
        - If a city is mentioned, extract the most likely city and its associated country (best guess).
        - Classify the forecast type based on temporal cues in the user's message.
        - If the time reference is vague or absent, default `forecast_type` to "current".
        - Only return the listed values exactly as specified in field options (e.g., "current", not "Current Weather").

        Always respond with all fields in proper JSON format.
    """

    has_city: bool = Field(
        description=(
            "True if the user's request mentions a city that needs to be converted to latitude/longitude. "
            "False if the user is asking about the weather without mentioning a city (e.g., local weather)."
        )
    )
    city_name: str = Field(
        description=(
            "The name of the city mentioned in the user's input. "
            "If no city is found, leave this as an empty string."
        )
    )
    country: str = Field(
        description=(
            "The country most commonly associated with the mentioned city. "
            "If no city is found, leave this as an empty string."
        )
    )
    forecast_type: Literal["current", "hourly", "daily"] = Field(
        description=(
            "The type of weather forecast the user is requesting:\n"
            "- 'current': The user is asking about weather right now or in the present moment.\n"
            "- 'hourly': The user is asking about weather conditions over the next few hours (within 24 hours).\n"
            "- 'daily': The user is asking about the forecast over multiple days (e.g., tomorrow, weekend, next 3 days).\n"
            "If uncertain or unspecified, default to 'current'."
        )
    )
    confidence_score: float = Field(description="Confidence score between 0 and 1, describing how sure the model is of its routing decision.")

load_dotenv()
# Weather_API_key = os.getenv("Weather_API")
api_key = os.getenv("LLM_API_KEY")


def get_open_meteo_forecast(lat:float, lon:float,forecast_type: Literal["hourly", "daily","current"] = "current") -> Dict:
    # Default to Cairo if no coordinates provided
    lat = lat if lat is not None else 30.0444
    lon = lon if lon is not None else 31.2357
    base_url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": "auto",
        # "current":"temperature_2m,wind_speed_10m"
    }
    try:
        if forecast_type == "hourly":
            params["hourly"] = "temperature_2m,apparent_temperature,precipitation,weathercode"
        elif forecast_type == "daily":
            params["daily"] = "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode"
        elif forecast_type == "current":
            params["current"] = "temperature_2m,wind_speed_10m,weathercode"
        else:
            raise ValueError("forecast_type must be 'hourly' or 'daily'.")

        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        if forecast_type == "hourly":
            return data["hourly"]
        elif forecast_type == "daily":
            return data["daily"]
        else :
            return data["current"]
    except Exception as err:
        print({"error at weather api": f"Request failed: {str(err)}"})
        return "error in weather response, please try again"

def get_location(city) -> dict:
    "converts city name to lon, lat"
    base_url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": city,
        "count": 1,
        "language": "en",
        "format":"json"
    }
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()
        if not data.get("results"):
            return {"error": "City not found. Please check the name and try again."}
        result = data["results"][0]
        # print(result)
        response = {
            'lon': result['longitude'],
            'lat': result['latitude'],
            'country': result['country']
        }
        return response
    except Exception as err:
        print({"error at geocoding api": f"Request failed: {str(err)}"})
        return "error in location conversion, please try again"


class WeatherTool:
    if not api_key:
        raise ValueError("Missing LLM_API_KEY. Did you forget to set it in your .env file?")
    def __init__(self):
        self.LLMmodel = genai.Client(api_key=api_key)
        # genai.configure(api_key=api_key)
        # self.LLMmodel = genai.GenerativeModel(
        #     model_name="models/gemini-2.5-flash",
        # )
    def get_weather_response(self,userInput,current_datetime,lat:float=None,lon:float=None) -> dict:
        try:
            messages = [types.Content(role="user", parts=[types.Part.from_text(text=userInput)])]
        
            city_name_response = self.LLMmodel.models.generate_content(
                model="gemini-2.5-flash",
                contents = messages,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": WeatherRequestSchema
                }
            )
            temp = json.loads(city_name_response.text)
            has_city = temp.get("has_city")
            # lon = lat = None
            if has_city:
                city = temp.get("city_name")
                expected_country = temp.get("country")
                converted_city_response = get_location(city)
                if converted_city_response["country"].lower() == expected_country.lower():
                    lon = converted_city_response["lon"]
                    lat = converted_city_response["lat"]
                else:
                    return "Error: Country mismatch. Please specify the country more clearly."

            # response = self.LLMmodel.generate_content(
            #     messages,
            #     generation_config={
            #         "response_mime_type": "application/json",
            #         "response_schema": RequestType
            #     }
            # )
            # result = json.loads(response.text)
            forecast_type = temp.get("forecast_type")
            # description = result.get("description", "No description provided")
            confidence_score = temp.get("confidence_score")
            print(f"[Routing Decision]: {forecast_type} | Confidence: {confidence_score}")
            forecast_data = get_open_meteo_forecast(lat,lon,forecast_type)
            print(f"Weather Api response: ",forecast_data)
            messages.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text=
                                "You are a helpful and friendly weather assistant. Your task is to analyze the provided weather forecast data "
                                "and generate a clear, human-readable summary that answers the user's question. "
                                "Always use a warm, easy-to-understand tone, and focus on making the response personalized and relevant.\n\n"

                                "Customize your response using the user's location and time:\n"
                                f"- Latitude: {lat}\n"
                                f"- Longitude: {lon}\n"
                                f"- Current Date and Time: {current_datetime}\n\n"

                                "Use the forecast data below to generate your answer. Include actionable or practical advice if appropriate "
                                "(e.g., bring an umbrella, wear light clothing).\n\n"

                                "--- Weather Forecast Data ---\n"
                                f"{forecast_data}\n\n"

                                "--- User Question ---\n"
                                f"{userInput}"
                        )
                    ]
                )
            )
            response = self.LLMmodel.models.generate_content(
                model="gemini-2.5-flash",
                contents = messages,
            )
            reply = response.text
            # messages.append({"role": "model", "parts": [reply]})
            return reply
        except Exception as err:
            print({"error at weather llm call": f"Request failed: {str(err)}"})
            return "error in weather llm call, please try again"


# userInput = input("Ask your weather-related question:")
# print(f"LLM response:",WeatherTool().get_weather_response(userInput))
# print(get_location("cairo"))



# print(f"--------------------------------------------------------")
# weather = get_current_weather(Weather_API_key)
# print(weather)


# def get_current_weather(api_key: str, lat=30.0444, lon=31.2357) -> dict:
#     if not api_key:
#         return {"error": "❌ API key is missing or not loaded from .env"}

#     url = "http://api.openweathermap.org/data/2.5/weather"
#     params = {
#         "lat": lat,
#         "lon": lon,
#         "appid": api_key,
#         "units": "metric",
#         # "exclude": "minutely,hourly,daily,alerts",
#         # "lang": "ar" "en"   #You can use this parameter to get the output in your language.
#     }

#     try:
#         response = requests.get(url, params=params, timeout=10)
#         data = response.json()

#         # If the response code is not 200 (OK), return the error message
#         if response.status_code != 200:
#             return {"error": f"{data.get('message', 'Unknown error')} (code {data.get('cod')})"}

#         return data["main"]

#     except Exception as err:
#         return {"error": f"Request failed: {str(err)}"}


# ---------------------------------------------------------------------------------------------------------

# class RequestType(BaseModel):
#     """Router LLM call: Determine the type of request"""

#     request_type: Literal[ "current", "hourly", "daily"] = Field(
#         description=(
#             "Classify the user's weather-related query into one of the following types:\n\n"
#             "1. **current** → The user is asking for the current weather conditions.\n"
#             "   Examples: 'What's the weather like right now?', 'Is it hot outside?', 'Do I need an umbrella now?'\n\n"
#             "2. **hourly** → The user is asking about the weather **within the next 24 hours**.\n"
#             "   Examples: 'Will it rain in the next few hours?', 'What's the weather like this evening?', 'Should I wear a jacket later?'\n\n"
#             "3. **daily** → The user is asking about the weather **over the next 1 or more full days**.\n"
#             "   Examples: 'What's the forecast for the next few days?', 'How's the weather tomorrow?', 'Will it be sunny this weekend?'\n\n"
#             "If the time range is not explicitly mentioned or implied in the user's query, default to **current**.\n\n"
#             "Based on the user input, return the most appropriate request_type, and a confidence score between 0 and 1."  #a cleaned description of the user’s intent,
#         )
#     )                
           
#     confidence_score: float = Field(description="Confidence score between 0 and 1, describing how sure the model is with his routing decision")
#     # description: str = Field(description="Cleaned description of the request")
