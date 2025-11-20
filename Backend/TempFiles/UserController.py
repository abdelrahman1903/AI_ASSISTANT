from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()
uri = os.getenv("DB_URL")
client = MongoClient(uri)

# Step 2: Choose database & collection
db = client["test_database"]      # Creates if doesn't exist
collection = db["test_collection"] # Creates if doesn't exist



# Step 3: Insert a sample document
doc = {
    "name": "John Doe",
    "email": "john@example.com",
    "role": "user"
}
result = collection.insert_one(doc)

print(f"Inserted document ID: {result.inserted_id}")
