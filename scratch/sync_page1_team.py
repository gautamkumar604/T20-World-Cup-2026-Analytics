import json

p1_slicer_path = 'power_bi/T20_World_Cup_2026_Analytics.Report/definition/pages/ReportSection_Page1_Overview/visuals/Slicer_Country/visual.json'
with open(p1_slicer_path, 'r', encoding='utf-8') as f:
    sdata = json.load(f)

sdata['visual']['syncGroup'] = {
    "groupName": "TeamSyncGroup",
    "fieldChanges": True,
    "filterChanges": True
}
sdata['visual']['query'] = {
    "queryState": {
        "Values": {
            "projections": [
                {
                    "field": {
                        "Column": {
                            "Expression": {
                                "SourceRef": {
                                    "Entity": "dim_teams"
                                }
                            },
                            "Property": "team_name"
                        }
                    },
                    "queryRef": "dim_teams.team_name",
                    "nativeQueryRef": "team_name",
                    "active": True
                }
            ]
        }
    }
}
sdata['filterConfig'] = {
    "filters": [
        {
            "name": "Filter_Team_Page1",
            "field": {
                "Column": {
                    "Expression": {
                        "SourceRef": {
                            "Entity": "dim_teams"
                        }
                    },
                    "Property": "team_name"
                }
            },
            "type": "Categorical"
        }
    ]
}

with open(p1_slicer_path, 'w', encoding='utf-8') as f:
    json.dump(sdata, f, indent=2)

print("Updated Page 1 Slicer to dim_teams.team_name with TeamSyncGroup!")
