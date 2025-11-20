import os
from elevenlabs import save
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv
from playsound import playsound


# Set your ElevenLabs API Key
load_dotenv()
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

class TTSTool:
    def elevenlabs_tts(self, text: str, output_file="output.mp3") -> bool:
        """
        Generate speech using ElevenLabs. Returns True if successful, False if quota is exceeded.

        voices list:
        Rachel — JBFqnCBsd6RMkjVDRZzb
        Domi — 2EiwWnXFnvU5JabPnv8n
        Bella — EXAVITQu4vr4xnSDxMaL
        """
        if not ELEVEN_API_KEY:
            raise ValueError("ElevenLabs API key must be provided.")
        client = ElevenLabs(api_key=ELEVEN_API_KEY)
        try:
            audio = client.text_to_speech.convert(
                text=text,
                voice_id="JBFqnCBsd6RMkjVDRZzb",
                # output_format="mp3_44100_128",
                model_id="eleven_multilingual_v2"
            )
            save(audio, output_file)
            playsound(output_file)  # Automatically play it
            return True
        except Exception  as e:
            print(f"[ElevenLabs] Error: {e}")
            return False



# TTSTool().elevenlabs_tts("Hello Zakzouk… I hope you're smiling, because today might be the last time you ever do.", output_file="ZakAi.mp3", language_code="en")
