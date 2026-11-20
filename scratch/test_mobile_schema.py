import urllib.request, json

url = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainerMobileState/1.0.0/schema.json'
req = urllib.request.Request(url, headers={'User-Agent': 'PowerBI'})
with urllib.request.urlopen(req) as resp:
    schema = json.loads(resp.read().decode('utf-8'))

test_obj = {
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainerMobileState/1.0.0/schema.json",
    "position": {
        "x": 10,
        "y": 10,
        "z": 1000,
        "width": 340,
        "height": 90
    }
}

req_top = schema.get('required', [])
print('Required top-level keys:', req_top)
for r in req_top:
    assert r in test_obj, f'Missing {r}'

pos_schema = schema['definitions']['VisualContainerPosition']
req_pos = pos_schema.get('required', [])
print('Required position keys:', req_pos)
for r in req_pos:
    assert r in test_obj['position'], f'Missing position key {r}'

for k in test_obj:
    assert k in schema['properties'], f'Invalid key {k}'
for k in test_obj['position']:
    assert k in pos_schema['properties'], f'Invalid position key {k}'

print('SCHEMA VALIDATION PASSED PERFECTLY!')
