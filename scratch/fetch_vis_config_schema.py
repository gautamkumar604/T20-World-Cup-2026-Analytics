import urllib.request
import json

url = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualConfiguration/2.0.0/schema-embedded.json'
req = urllib.request.Request(url, headers={'User-Agent': 'PowerBI'})
with urllib.request.urlopen(req) as resp:
    schema = json.loads(resp.read().decode('utf-8'))

print('Root keys:', list(schema.keys()))
print('Properties:', list(schema.get('properties', {}).keys()))
print('Definitions in visualConfiguration:', list(schema['definitions'].keys()))
for k in schema['definitions']:
    if 'filter' in k.lower() or 'top' in k.lower():
        print(k, json.dumps(schema['definitions'][k], indent=2))
