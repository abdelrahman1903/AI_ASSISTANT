import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
api_key = os.getenv("LLM_API_KEY")

# Check if API key is loaded
if not api_key:
    raise ValueError("LLM_API_KEY not found in .env file")

# Configure the Generative AI SDK with the API key
genai.configure(api_key=api_key)

# List all available models
models = genai.list_models()

# Print model names
for model in models:
    print(model.name)