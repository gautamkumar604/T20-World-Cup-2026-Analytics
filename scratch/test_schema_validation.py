import urllib.request
import json
import jsonschema

# Fetch schemas
base_url = 'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/'
def fetch(rel):
    req = urllib.request.Request(base_url + rel, headers={'User-Agent': 'PowerBI'})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode('utf-8'))

schema_vis = fetch('visualContainer/2.0.0/schema.json')
schema_fc = fetch('filterConfiguration/1.1.0/schema-embedded.json')
schema_sq = fetch('semanticQuery/1.2.0/schema.json')
schema_vc = fetch('visualConfiguration/2.0.0/schema-embedded.json')

# Build resolver
schema_store = {
    schema_vis['$id']: schema_vis,
    'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.0.0/schema.json': schema_vis,
    '../../filterConfiguration/1.1.0/schema-embedded.json': schema_fc,
    'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/filterConfiguration/1.1.0/schema-embedded.json': schema_fc,
    '../../semanticQuery/1.2.0/schema.json': schema_sq,
    'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/semanticQuery/1.2.0/schema.json': schema_sq,
    '../../visualConfiguration/2.0.0/schema-embedded.json': schema_vc,
    'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualConfiguration/2.0.0/schema-embedded.json': schema_vc
}

resolver = jsonschema.RefResolver.from_schema(schema_fc, store=schema_store)

test_filter_1 = {
    "name": "FilterTop5_Table_TopRunScorers",
    "field": {
        "Column": {
            "Expression": {
                "SourceRef": {
                    "Entity": "fact_batting_scorecards"
                }
            },
            "Property": "player_name"
        }
    },
    "type": "TopN"
}

try:
    jsonschema.validate(instance={"filters": [test_filter_1]}, schema=schema_fc, resolver=resolver)
    print("Test 1 (name, field, type: TopN) VALID!")
except Exception as e:
    print("Test 1 INVALID:", e)

test_filter_2 = {
    "name": "FilterTop5_Table_TopRunScorers",
    "field": {
        "Column": {
            "Expression": {
                "SourceRef": {
                    "Entity": "fact_batting_scorecards"
                }
            },
            "Property": "player_name"
        }
    },
    "type": "TopN",
    "filter": {
        "Version": 2,
        "From": [
            {
                "Name": "fact_batting_scorecards",
                "Entity": "fact_batting_scorecards",
                "Type": 0
            }
        ],
        "Where": [
            {
                "Condition": {
                    "VisualTopN": {
                        "ItemCount": 5
                    }
                }
            }
        ]
    }
}

try:
    jsonschema.validate(instance={"filters": [test_filter_2]}, schema=schema_fc, resolver=resolver)
    print("Test 2 (with filter.VisualTopN) VALID!")
except Exception as e:
    print("Test 2 INVALID:", e)
