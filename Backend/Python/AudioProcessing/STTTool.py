import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
# from datasets import load_dataset
import torchaudio
import os
from .TTSTool import TTSTool
from .Temp_TTSTool import TTSWrapper


class STTTool:
    def __init__(self):
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        model_id = "openai/whisper-large-v3-turbo"

        self.device = device
        self.torch_dtype = torch_dtype
        self.processor = AutoProcessor.from_pretrained(model_id)
        self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True
        ).to(device)

        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=self.model,
            tokenizer=self.processor.tokenizer,
            feature_extractor=self.processor.feature_extractor,
            torch_dtype=torch_dtype,
            device=device,
        )
    def generate_response(self,uploaded_file_path: str, language: str = None):
        # print("in whisper: "+user_audio_path)
        try:
            waveform, sample_rate = torchaudio.load(uploaded_file_path)
            
            # Hugging Face expects a dictionary like this:
            sample = {
                "array": waveform.squeeze().numpy(),  # Convert to 1D NumPy array
                "sampling_rate": sample_rate
            }

            # Set language detection if not provided
            kwargs = {}
            if language:
                kwargs["generate_kwargs"] = {"language": language}

            # Transcribe
            result = self.pipe(sample, **kwargs)
            return result["text"]
        except Exception as e:
            print(f"❌ Error transcribing audio: {e}")
            return "❌ Error transcribing audio, please try again"
        # finally:
        #     # Delete temp audio after transcription
        #     if uploaded_file_path and os.path.exists(uploaded_file_path):
        #         os.remove(uploaded_file_path)


# text = STTTool().generate_response("TempAudioFils/temp_audioA.wav","arabic")
# print("🔊 Transcription:", text)
# # TTSTool().elevenlabs_tts(text,"ZakAi.mp3")
# tts_inst = TTSWrapper()
# tts_inst.generate_speech(text, "TTS_slow_Tool.wav", language="en",speaker_wav="speaker.wav")



# very important
# pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

