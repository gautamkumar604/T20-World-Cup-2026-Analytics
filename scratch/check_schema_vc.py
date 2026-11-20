import json, urllib.request

schema_url = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.14.0/schema.json"
try:
    with urllib.request.urlopen(schema_url) as resp:
        schema = json.loads(resp.read().decode('utf-8'))
    print("Schema loaded successfully. Keys:", list(schema.keys()))
except Exception as e:
    print("Error:", e)
