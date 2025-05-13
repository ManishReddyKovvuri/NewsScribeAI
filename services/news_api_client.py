"""Wrapper over external news sources"""
import httpx
import os 
from dotenv import load_dotenv
load_dotenv()



newsdata_api_key = os.getenv('NEWSDATA_API_KEY')
print(newsdata_api_key)
response = httpx.get(f"https://newsdata.io/api/1/latest?apikey={newsdata_api_key}&full_content=1")

print(response)  # Output: <Response [200 OK]>
print(response.json())
