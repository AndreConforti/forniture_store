import requests
import json

url = "https://api.cosmos.bluesoft.com.br/gtins/7891910000197"

payload = {}
headers = {
  'X-Cosmos-Token': 'HbEOldRUAZZxLS0tYyXnIA',
  'Content-Type': 'application/json',
  'User-Agent': 'Cosmos-API-Request'
}

response = requests.request("GET", url, headers=headers, data=payload)

print(response.text)
