from diffusers import StableDiffusionPipeline
import torch

pipe = StableDiffusionPipeline.from_pretrained("runwayml/stable-diffusion-v1-5")
device = "cuda" if torch.cuda.is_available() else "cpu"
pipe = pipe.to(device)


class ImageGeneration:
    @staticmethod
    def generate_image(prompt: str, output_path: str = "output.png"):
        try:
            image = pipe(
                prompt,
                num_inference_steps=140 if device == "cuda" else 50,  # More steps for GPU
                guidance_scale=12 if device == "cuda" else 7.5,  # Stronger guidance for GPU
            ).images[0]

            image.save(output_path)
            return output_path
        except Exception as e:
            print(f"❌ Error generating image: {e}")
            return f"❌ Error generating image, please try again"




ImageGeneration.generate_image(
    "generate a high quality, realist Formula ! racing car the is driving in the track at night",
    "image.png"
)