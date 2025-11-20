from transformers import Qwen3VLForConditionalGeneration, AutoProcessor
import torch

# We recommend enabling flash_attention_2 for better acceleration and memory saving, especially in multi-image and video scenarios.
# model = Qwen3VLForConditionalGeneration.from_pretrained(
#     "Qwen/Qwen3-VL-2B-Instruct",
#     dtype=torch.bfloat16,
#     attn_implementation="flash_attention_2",
#     device_map="auto",
# )

device = "cuda:0" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
model_id =  "Qwen/Qwen3-VL-2B-Instruct"
device = device
torch_dtype = torch_dtype
processor = AutoProcessor.from_pretrained(model_id)
model = Qwen3VLForConditionalGeneration.from_pretrained(
    model_id,
    torch_dtype=torch_dtype,
    # attn_implementation="flash_attention_2",
    device_map="auto",
    use_safetensors=True
)

class ImageProcessing:
    @staticmethod
    def generate_response(img_path: str, text: str):
        # image = Image.open(img_path).convert("RGB")
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "image": img_path,
                    },
                    {"type": "text", "text": text},
                ],
            }
        ]
        # Preparation for inference
        inputs = processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt"
        )
        inputs = inputs.to(model.device)

        # Inference: Generation of the output
        generated_ids = model.generate(**inputs, max_new_tokens=128)
        generated_ids_trimmed = [
            out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )
        print(output_text)
        return output_text[0]




# path = r"C:\Users\abdel\Downloads\github_repo.png"
# ImageProcessing.generate_response(path, "what are the names of the repositories shown in the image?")
