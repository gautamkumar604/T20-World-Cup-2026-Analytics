import urllib.request
import json

url = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualConfiguration/2.0.0/schema-embedded.json'
req = urllib.request.Request(url, headers={'User-Agent': 'PowerBI'})
with urllib.request.urlopen(req) as resp:
    schema = json.loads(resp.read().decode('utf-8'))

vqo = schema['definitions']['VisualQueryOptions']
print('VisualQueryOptions:', json.dumps(vqo, indent=2))
