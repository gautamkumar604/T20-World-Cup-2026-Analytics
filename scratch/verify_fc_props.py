import urllib.request
import json

# Let's inspect the exact allowed schema properties
url_fc = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/filterConfiguration/1.1.0/schema-embedded.json'
req = urllib.request.Request(url_fc, headers={'User-Agent': 'PowerBI'})
with urllib.request.urlopen(req) as resp:
    fc_schema = json.loads(resp.read().decode('utf-8'))

print("FilterContainer allowed properties:")
for p in fc_schema['definitions']['FilterContainer']['properties']:
    print(" ", p)
