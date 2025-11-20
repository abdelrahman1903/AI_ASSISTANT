import base64
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, UploadFile, File, Form, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from Model import Model 
from AudioProcessing.STTTool import STTTool
from AudioProcessing.TTSTool import TTSTool
# from AudioProcessing.Temp_TTSTool import TTSWrapper
import os
from dotenv import load_dotenv
import shutil
from pydub import AudioSegment
# from RAG.Chunking import Chunking
import json
from Session import Session
from apscheduler.schedulers.background import BackgroundScheduler
from ImageProcessing.ImageProcessing import ImageProcessing

from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import requests


load_dotenv()
FastAPI_port = os.getenv("FASTAPI_PORT")
node_port = os.getenv("NODE_PORT")

# mail tool env variables
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  #⚠️⚠️ Only for local testing
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
# Scopes define what permissions your app will request (read + send emails)
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", "https://www.googleapis.com/auth/gmail.send","openid","https://www.googleapis.com/auth/userinfo.email"]

whisper_instance = STTTool()
TTSTool_instance = TTSTool()
# slow_TTS_instance = TTSWrapper()
# model_instance = Model()

app = FastAPI()
scheduler = BackgroundScheduler()


def cleanup_sessions():
    Session.remove_idle_sessions()

# def Read_Emails():
#     Session.remove_idle_sessions()

scheduler.add_job(cleanup_sessions, "interval", minutes=1)
scheduler.start()



# Allow frontend to access backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "FastAPI is running!"}

@app.post("/chat")  # ✅ Change to POST
async def chat(request: Request,authorization: str = Header(None)):
    if authorization is None:
        return {"status_code":401, "response": "Missing token"}
    # print("bearer token received:", authorization)
    data = await request.json()
    user_text = data.get("text")
    # user_id = data.get("id")
    if not user_text:
        return {"error": "No input text provided."}
    location = data.get("location")  #⚠️⚠️To-do fetch location from frontEnd
    print("location data:",data.get("location"))
    # location = { "latitude": 29.9866, "longitude": 31.4406 } #⚠️⚠️To-do remove this line when location is fetched from frontend
    # print(f"Received token: '{authorization}'")
    # for s in Session.sessions:
    #     print(f"Existing token: '{s['Token']}'")
    model_instance = Session.user_chatBot_instance(authorization,location)
    # Access the model instance from app.state
    response = model_instance.generate_response(user_text,location,authorization)

    return {"response": response}  # ✅ Ensure the correct response field


#⚠️⚠️to do: file names should use userid for files to be unique
@app.post("/audio")  # ✅ Change to POST
async def chat(audio: UploadFile = File(...),authorization: str = Header(None)):
    if authorization is None:
        return {"status_code":401, "response": "Missing token"}
    
    input_path = "temp_input"  + authorization + ".webm" # Save raw uploaded file
    wav_path = "temp_audio"   + authorization + ".wav" # Will convert to this
    with open(input_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)
    audio_segment = AudioSegment.from_file(input_path)
    audio_segment = audio_segment.set_frame_rate(16000).set_channels(1)  # Ensure 16kHz mono for Whisper
    audio_segment.export(wav_path, format="wav")
    text = whisper_instance.generate_response(wav_path)
    # is_voice_generated = TTSTool_instance.elevenlabs_tts(text,wav_path)
    # if not is_voice_generated :
    #     slow_TTS_instance.generate_speech(text,wav_path,"en","speaker.wav") #⚠️⚠️language to be input instead of hard coded
    os.remove(input_path)
    os.remove(wav_path)
    return {"Transcription": text}  # ✅ Ensure the correct response field

#⚠️⚠️to do: file names should use userid for files to be unique
# @app.post("/audio")
# async def process_audio(request: Request): # audio: UploadFile = File(...)
#     input_path = "temp_input.webm"  # Save raw uploaded file
#     data = await request.json()
#     input_path = data.get("input")
#     output_path = data.get("output")     # Will convert to this
#     lan = data.get("language")
#     lan_code = lan[:2] if lan else None
#     flag = data.get("flag")

#     text = whisper_instance.generate_response(input_path,lan)
#     is_voice_generated = False
#     if flag:
#         is_voice_generated = TTSTool_instance.elevenlabs_tts(text,f"{output_path}.mp3")
#     # if not is_voice_generated :
#     #     if lan == "german":
#     #         lan_code = "de"
#     #     slow_TTS_instance.generate_speech(text,f"{output_path}.wav",lan_code,"AudioProcessing/speaker.wav") #⚠️⚠️language to be input instead of hard coded
#     # os.remove(input_path)
#     # os.remove(wav_path)
#     return {"Transcription": text}  # ✅ Ensure the correct response field



# @app.post("/upload")
# async def upload_file(file: UploadFile = File(...), message: str = Form(...)):
#     with open(f"uploads/{file.filename}", "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)
#     parsed_message = json.loads(message)
#     response = Chunking.LLM_Response(parsed_message,f"uploads/{file.filename}")    
#     return {"response": response}



@app.post("/image_processing")
async def process_image(request: Request, authorization: str = Header(None)):
    
    if authorization is None:
        return {"status_code":401, "response": "Missing token"}
    
    data = await request.json()
    image_path = data.get("image")
    user_text = data.get("text")

    if not user_text or not image_path:
        return {"error": "No input text or image path provided."}
    response = ImageProcessing.generate_response(image_path,user_text)

    # ⚠️⚠️ check if this is a new session if yes retrive history first
    # location = data.get("location") ⚠️⚠️To-do fetch location from frontEnd
    location = { "latitude": 29.9866, "longitude": 31.4406 } #⚠️⚠️To-do remove this line when location is fetched from frontend
    model_instance = Session.user_chatBot_instance(authorization, location)

    model_instance.add_message("user", user_text)
    model_instance.add_message("model", response)

    return {"caption": response}  # ✅ Ensure the correct response field


@app.get("/auth")
def auth(request: Request):
    token = request.query_params.get("token")
    authorization = "Bearer " + token  # 🔥 FIX HERE
    print("in auth")
    if authorization is None:
        return {"status_code":401, "response": "Missing token"}
    
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI], # Allowed redirect URIs (must match Google Cloud)
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
    )
    # Set the specific redirect URI for this session
    flow.redirect_uri = REDIRECT_URI
    
    url = f"http://localhost:{node_port}/api/v1/fastapi/getemail"  
    # Optional headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": authorization
    }


    response = requests.get(url,headers=headers)  #headers=headers, data=json.dumps(payload)
    if response.status_code == 200 :
        print("✅ Retrieved email from Node.js backend.:", response.json())
        data = response.json()
        email = data['data']['email']
        print(f"✅ Retrieved email: {email}")

        state_payload = {
            "token": authorization,   # your Bearer token
            "email": email            # user's email
        }

        # Encode to base64 so Google accepts it safely
        state_encoded = base64.urlsafe_b64encode(
            json.dumps(state_payload).encode()
        ).decode()

        authorization_url, state = flow.authorization_url(
            access_type="offline", # Get refresh token for long-term access
            include_granted_scopes="true",
            prompt="consent", #⚠️⚠️ Forces the consent screen to appear each time — good for testing. You can remove it later for production.
            state=state_encoded,        # <---- YOUR TOKEN HERE
            login_hint=email  # <-- hint Google which account to select
        )
        return RedirectResponse(authorization_url)
    
    else:
        print("❌ Failed to retrieve email from Node.js backend.")
        return JSONResponse({"status": "error", "message": "Failed to retrieve email"}, status_code=500)

@app.get("/auth/callback")
def auth_callback(request: Request):
    code = request.query_params.get("code")
    # user_token = request.query_params.get("state")  # 🔥 Retrieve user id

    state_encoded = request.query_params.get("state")

    # Decode back to JSON
    decoded = json.loads(
        base64.urlsafe_b64decode(state_encoded.encode()).decode()
    )

    user_token = decoded["token"]
    email = decoded["email"]

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uris": [REDIRECT_URI],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = REDIRECT_URI

    flow.fetch_token(code=code)
    credentials = flow.credentials

    # -------------------------------------------------------
    # ✅ STEP 1: Get authenticated Google email
    # -------------------------------------------------------
    userinfo = requests.get(
        "https://www.googleapis.com/oauth2/v1/userinfo?alt=json",
        headers={"Authorization": f"Bearer {credentials.token}"}
    ).json()

    google_email = userinfo.get("email")
    print("Google authenticated email :", google_email)
    print("Expected email from state  :", email)

    # -------------------------------------------------------
    # ✅ STEP 2: Verify email matches the one provided
    # -------------------------------------------------------
    if google_email.lower() != email.lower():
        print("❌ Email mismatch! OAuth rejected.")
        return JSONResponse(
            {
                "status": "error",
                "message": (
                    f"Invalid Google account. "
                    f"Expected: {email}, but authenticated: {google_email}"
                )
            },
            status_code=400
        )
    
    # -------------------------------------------------------
    # Continue with saving OAuth info to Node.js backend
    # -------------------------------------------------------

    url = f"http://localhost:{node_port}/api/v1/fastapi/setUserOAuthInfo"  
        # Optional headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": user_token
    }
    # Ensure credentials.expiry is timezone-aware in UTC
    expiry_utc = credentials.expiry
    if expiry_utc.tzinfo is None:
        expiry_utc = expiry_utc.replace(tzinfo=timezone.utc)
    else:
        expiry_utc = expiry_utc.astimezone(timezone.utc)
    payload = {
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "access_token_expiry": expiry_utc.isoformat(),  # UTC ISO string with Z
        "is_authenticated": True
    }
    response = requests.post(url,headers=headers,json=payload)  #headers=headers, data=json.dumps(payload)
    if response.status_code == 200 :
        print("✅ User OAuth info set successfully in Node.js backend.")
    else:
        print("❌ Failed to set User OAuth info in Node.js backend.")
        return JSONResponse({"status": "error", "message": "Failed to set OAuth info"}, status_code=500)

    # return JSONResponse({
    #     "access_token": credentials.token,
    #     "refresh_token": credentials.refresh_token,
    #     "token_uri": credentials.token_uri,
    #     "client_id": credentials.client_id,
    #     "client_secret": credentials.client_secret
    # })
    return RedirectResponse("http://localhost:3000/oauth-success")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=FastAPI_port)
