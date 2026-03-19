import requests
import json

url = "http://localhost:8001/generate"
from dotenv import load_dotenv
load_dotenv(override=True)
import os
from product_service import call_llm, generate_product_plan

api_key = os.getenv("GROQ_API_KEY", "")
print(f"Loaded key manually: {api_key[:10]}...{api_key[-4:] if len(api_key) > 4 else ''}")

try:
    print("Directly calling generate_product_plan()...")
    res = generate_product_plan("Build a platform that helps college students find verified internships")
    print("Success! Got parsed response:")
    print(json.dumps(res, indent=2))
except Exception as e:
    print("FAILED with exception:", str(e))
