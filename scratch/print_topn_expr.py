import urllib.request
import json

url = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/semanticQuery/1.2.0/schema.json'
req = urllib.request.Request(url, headers={'User-Agent': 'PowerBI'})
with urllib.request.urlopen(req) as resp:
    schema = json.loads(resp.read().decode('utf-8'))

print(json.dumps(schema['definitions']['QueryVisualTopNExpression'], indent=2))
