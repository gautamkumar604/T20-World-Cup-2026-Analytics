import urllib.request
import json

url = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/semanticQuery/1.2.0/schema.json'
req = urllib.request.Request(url, headers={'User-Agent': 'PowerBI'})
with urllib.request.urlopen(req) as resp:
    schema = json.loads(resp.read().decode('utf-8'))

if 'VisualTopN' in schema.get('definitions', {}):
    print('VisualTopN definition:', json.dumps(schema['definitions']['VisualTopN'], indent=2))
else:
    for k, v in schema.get('definitions', {}).items():
        if 'VisualTopN' in json.dumps(v):
            print('VisualTopN found in:', k)
            if 'properties' in v and 'VisualTopN' in v['properties']:
                print(json.dumps(v['properties']['VisualTopN'], indent=2))

if 'Top' in schema.get('definitions', {}).get('QueryDefinition', {}).get('properties', {}):
    print('QueryDefinition.Top:', json.dumps(schema['definitions']['QueryDefinition']['properties']['Top'], indent=2))
