from fastapi import FastAPI, UploadFile, File, Form, Request
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from Model import Model  # Ensure you have a Model class defined in model.py
from STTTool import STTTool
from TTSTool import TTSTool
from Temp_TTSTool import TTSWrapper
import os
from dotenv import load_dotenv
import shutil
from pydub import AudioSegment
# from RAG.Chunking import Chunking
import json

load_dotenv()
uri = os.getenv("DB_URL")
# Define request body structure
# class TextRequest(BaseModel):
#     text: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.mongodb_client = AsyncIOMotorClient(uri)
    app.mongodb = app.mongodb_client["test_database"]
    # test_collection = app.mongodb["test_collection"]
    # # Step 3: Insert a sample document
    # doc = {
    #     "name": "Zakzouk",
    #     "email": "test@example.com",
    #     "role": "admin"
    # }
    # result = test_collection.insert_one(doc)
    print("✅ Connected to MongoDB Atlas")

    # Store tool instances in app.state so they are accessible in routes
    app.state.whisper_instance = STTTool()
    app.state.TTSTool_instance = TTSTool()
    app.state.slow_TTS_instance = TTSWrapper()
    app.state.model_instance = Model()
    print("✅ All tools initialized")

    yield  # Wait here while the app runs

    # Shutdown
    app.mongodb_client.close()
    print("🛑 MongoDB connection closed")

app = FastAPI(lifespan=lifespan)


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
async def chat(request: Request):
    data = await request.json()
    user_text = data.get("text")
    if not user_text:
        return {"error": "No input text provided."}
    # location = data.get("location")
    location = { "latitude": 29.9866, "longitude": 31.4406 }

    # Access the model instance from app.state
    model_instance = request.app.state.model_instance
    response = model_instance.generate_response(user_text,location)

    return {"response": response}  # ✅ Ensure the correct response field


# #⚠️⚠️to do: file names should use userid for files to be unique
# @app.post("/audio")  # ✅ Change to POST
# async def chat(audio: UploadFile = File(...)):
#     input_path = "temp_input.webm"  # Save raw uploaded file
#     wav_path = "temp_audio.wav"     # Will convert to this
#     with open(input_path, "wb") as buffer:
#         shutil.copyfileobj(audio.file, buffer)
#     audio_segment = AudioSegment.from_file(input_path)
#     audio_segment = audio_segment.set_frame_rate(16000).set_channels(1)  # Ensure 16kHz mono for Whisper
#     audio_segment.export(wav_path, format="wav")
#     text = whisper_instance.generate_response("temp_audio.wav")
#     is_voice_generated = TTSTool_instance.elevenlabs_tts(text,wav_path)
#     if not is_voice_generated :
#         slow_TTS_instance.generate_speech(text,wav_path,"en","speaker.wav") #⚠️⚠️language to be input instead of hard coded
#     os.remove(input_path)
#     os.remove(wav_path)
#     return {"Transcription": text}  # ✅ Ensure the correct response field

#⚠️⚠️to do: file names should use userid for files to be unique
@app.post("/audio")  # ✅ Change to POST
async def process_audio(request: Request): # audio: UploadFile = File(...)
    input_path = "temp_input.webm"  # Save raw uploaded file
    data = await request.json()
    input_path = data.get("input")
    output_path = data.get("output")     # Will convert to this
    lan = data.get("language")
    lan_code = lan[:2] if lan else None
    flag = data.get("flag")

    whisper_instance = request.app.state.whisper_instance
    text = whisper_instance.generate_response(input_path,lan)
    is_voice_generated = False
    if flag:
        TTSTool_instance = request.app.state.TTSTool_instance
        is_voice_generated = TTSTool_instance.elevenlabs_tts(text,f"{output_path}.mp3")
    if not is_voice_generated :
        if lan == "german":
            lan_code = "de"
        slow_TTS_instance = request.app.state.slow_TTS_instance
        slow_TTS_instance.generate_speech(text,f"{output_path}.wav",lan_code,"speaker.wav") #⚠️⚠️language to be input instead of hard coded
    # os.remove(input_path)
    # os.remove(wav_path)
    return {"Transcription": text}  # ✅ Ensure the correct response field



# @app.post("/upload")
# async def upload_file(file: UploadFile = File(...), message: str = Form(...)):
#     with open(f"uploads/{file.filename}", "wb") as buffer:
#         shutil.copyfileobj(file.file, buffer)
#     parsed_message = json.loads(message)
#     response = Chunking.LLM_Response(parsed_message,f"uploads/{file.filename}")    
#     return {"response": response}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


# @app.get("/chat")  # ✅ Change to POST
# async def chat(txt: str):
#     location = { "latitude": 29.9866, "longitude": 31.4406 }
#     response = model_instance.generate_response(txt,location)
#     return {"response": response}  # ✅ Ensure the correct response field
