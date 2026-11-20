import urllib.request
import json

url = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json'
req = urllib.request.Request(url, headers={'User-Agent': 'PowerBI'})
with urllib.request.urlopen(req) as resp:
    schema = json.loads(resp.read().decode('utf-8'))

vis = schema['properties']['visual']
print('visual properties:', list(vis.get('properties', {}).keys()))
for k, v in vis.items():
    print(k, v)
