import json
import os

BIM_PATH = 'power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim'
M_PATH = 'power_bi/power_query_m_code.m'

with open(BIM_PATH, 'r', encoding='utf-8') as f:
    bim_data = json.load(f)

# Check if view_tournament_standings already exists
existing_tables = [t['name'] for t in bim_data['model']['tables']]
print("Existing tables in model.bim:", existing_tables)

table_def = {
    "name": "view_tournament_standings",
    "columns": [
        {"name": "stage_normalized", "dataType": "string", "sourceColumn": "stage_normalized", "isNullable": False},
        {"name": "group_name", "dataType": "string", "sourceColumn": "group_name", "isNullable": False},
        {"name": "pool_rank", "dataType": "int64", "sourceColumn": "pool_rank", "isNullable": False},
        {"name": "team_name", "dataType": "string", "sourceColumn": "team_name", "isNullable": False},
        {"name": "played", "dataType": "int64", "sourceColumn": "played", "isNullable": False},
        {"name": "wins", "dataType": "int64", "sourceColumn": "wins", "isNullable": False},
        {"name": "losses", "dataType": "int64", "sourceColumn": "losses", "isNullable": False},
        {"name": "no_result", "dataType": "int64", "sourceColumn": "no_result", "isNullable": False},
        {"name": "points", "dataType": "int64", "sourceColumn": "points", "isNullable": False},
        {"name": "nrr_display", "dataType": "double", "sourceColumn": "nrr_display", "formatString": "+#,0.000;-#,0.000;0.000", "isNullable": True},
        {"name": "safe_h2h_points", "dataType": "int64", "sourceColumn": "safe_h2h_points", "isNullable": True},
        {"name": "h2h_nrr_display", "dataType": "double", "sourceColumn": "h2h_nrr_display", "formatString": "+#,0.000;-#,0.000;0.000", "isNullable": True},
        {"name": "icc_rank", "dataType": "int64", "sourceColumn": "icc_rank", "isNullable": True},
        {"name": "resolution_step", "dataType": "string", "sourceColumn": "resolution_step", "isNullable": False},
        {"name": "qualification_status", "dataType": "string", "sourceColumn": "qualification_status", "isNullable": False},
        {"name": "runs_scored", "dataType": "double", "sourceColumn": "runs_scored", "isNullable": True},
        {"name": "balls_faced", "dataType": "int64", "sourceColumn": "balls_faced", "isNullable": True},
        {"name": "runs_conceded", "dataType": "double", "sourceColumn": "runs_conceded", "isNullable": True},
        {"name": "balls_bowled", "dataType": "int64", "sourceColumn": "balls_bowled", "isNullable": True},
        {"name": "nrr_num", "dataType": "double", "sourceColumn": "nrr_num", "isNullable": True},
        {"name": "nrr_den", "dataType": "double", "sourceColumn": "nrr_den", "isNullable": True},
        {"name": "nrr_canon_num", "dataType": "double", "sourceColumn": "nrr_canon_num", "isNullable": True},
        {"name": "nrr_canon_den", "dataType": "double", "sourceColumn": "nrr_canon_den", "isNullable": True}
    ],
    "partitions": [
        {
            "name": "view_tournament_standings-Partition",
            "mode": "import",
            "source": {
                "type": "m",
                "expression": [
                    "let\n",
                    "    Source = PostgreSQL.Database(\"localhost\", \"t20_worldcup_2026\"),\n",
                    "    public_view_tournament_standings = Source{[Schema=\"public\",Item=\"view_tournament_standings\"]}[Data],\n",
                    "    #\"Changed Type\" = Table.TransformColumnTypes(public_view_tournament_standings,{\n",
                    "        {\"stage_normalized\", type text},\n",
                    "        {\"group_name\", type text},\n",
                    "        {\"pool_rank\", Int64.Type},\n",
                    "        {\"team_name\", type text},\n",
                    "        {\"played\", Int64.Type},\n",
                    "        {\"wins\", Int64.Type},\n",
                    "        {\"losses\", Int64.Type},\n",
                    "        {\"no_result\", Int64.Type},\n",
                    "        {\"points\", Int64.Type},\n",
                    "        {\"nrr_display\", type number},\n",
                    "        {\"safe_h2h_points\", Int64.Type},\n",
                    "        {\"h2h_nrr_display\", type number},\n",
                    "        {\"icc_rank\", Int64.Type},\n",
                    "        {\"resolution_step\", type text},\n",
                    "        {\"qualification_status\", type text},\n",
                    "        {\"runs_scored\", type number},\n",
                    "        {\"balls_faced\", Int64.Type},\n",
                    "        {\"runs_conceded\", type number},\n",
                    "        {\"balls_bowled\", Int64.Type},\n",
                    "        {\"nrr_num\", type number},\n",
                    "        {\"nrr_den\", type number},\n",
                    "        {\"nrr_canon_num\", type number},\n",
                    "        {\"nrr_canon_den\", type number}\n",
                    "    })\n",
                    "in\n",
                    "    #\"Changed Type\"\n"
                ]
            }
        }
    ]
}

if 'view_tournament_standings' in existing_tables:
    idx = [i for i, t in enumerate(bim_data['model']['tables']) if t['name'] == 'view_tournament_standings'][0]
    bim_data['model']['tables'][idx] = table_def
    print("Updated existing view_tournament_standings in model.bim")
else:
    bim_data['model']['tables'].append(table_def)
    print("Added view_tournament_standings to model.bim")

with open(BIM_PATH, 'w', encoding='utf-8') as f:
    json.dump(bim_data, f, indent=2)

print("Saved model.bim successfully.")

# Update power_query_m_code.m
with open(M_PATH, 'r', encoding='utf-8') as f:
    m_content = f.read()

m_addition = """
// Table: view_tournament_standings
let
    Source = PostgreSQL.Database("localhost", "t20_worldcup_2026"),
    public_view_tournament_standings = Source{[Schema="public",Item="view_tournament_standings"]}[Data],
    #"Changed Type" = Table.TransformColumnTypes(public_view_tournament_standings,{
        {"stage_normalized", type text},
        {"group_name", type text},
        {"pool_rank", Int64.Type},
        {"team_name", type text},
        {"played", Int64.Type},
        {"wins", Int64.Type},
        {"losses", Int64.Type},
        {"no_result", Int64.Type},
        {"points", Int64.Type},
        {"nrr_display", type number},
        {"safe_h2h_points", Int64.Type},
        {"h2h_nrr_display", type number},
        {"icc_rank", Int64.Type},
        {"resolution_step", type text},
        {"qualification_status", type text},
        {"runs_scored", type number},
        {"balls_faced", Int64.Type},
        {"runs_conceded", type number},
        {"balls_bowled", Int64.Type},
        {"nrr_num", type number},
        {"nrr_den", type number},
        {"nrr_canon_num", type number},
        {"nrr_canon_den", type number}
    })
in
    #"Changed Type"
"""

if "view_tournament_standings" not in m_content:
    with open(M_PATH, 'a', encoding='utf-8') as f:
        f.write("\n" + m_addition)
    print("Appended view_tournament_standings M query to power_query_m_code.m")
else:
    print("view_tournament_standings already in power_query_m_code.m")
