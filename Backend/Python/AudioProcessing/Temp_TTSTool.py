from TTS.api import TTS
import torch
from playsound import playsound

class TTSWrapper:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tts = TTS(model_name="tts_models/multilingual/multi-dataset/xtts_v2", progress_bar=False).to(self.device)

    def generate_speech(self, text, output_file, language="en", speaker_wav=None):
        try:
            self.tts.tts_to_file(
                text=text,
                file_path=output_file,
                language=language,
                speaker_wav=speaker_wav
            )
            playsound(output_file)  # Automatically play it
        except Exception as e:
            print(f"❌ Error converting text to speech : {e}")
            return f"❌ Error converting text to speech, please try again"

# tts_inst = TTSWrapper()
# tts_inst.generate_speech("Hello this is ZakAi talking, your personal assistant how can I help you today Zakzouk.", "TTS_slow_Tool.wav", language="en",speaker_wav="speaker.wav")
# tts_inst.generate_speech("Hello this is ZakAi talking, your personal assistant how can I help you today Zakzouk.", "Bnglish.wav", language="en",speaker_wav="speaker.wav")