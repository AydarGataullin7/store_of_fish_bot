import requests
import os
from dotenv import load_dotenv

load_dotenv()

url = 'http://localhost:1337/api/products'
headers = {"Authorization": f"Bearer {os.getenv('STRAPI_TOKEN')}"}
response = requests.get(url, headers=headers)

print(response.json())
