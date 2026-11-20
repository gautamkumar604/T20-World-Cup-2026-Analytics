import json

BIM_PATH = 'power_bi/T20_World_Cup_2026_Analytics.SemanticModel/model.bim'
M_PATH = 'power_bi/power_query_m_code.m'
REPORT_PATH = 'power_bi/T20_World_Cup_2026_Analytics.Report/report.json'

# 1. Update model.bim
with open(BIM_PATH, 'r', encoding='utf-8') as f:
    bim = json.load(f)

st_table = [t for t in bim['model']['tables'] if t['name'] == 'view_tournament_standings'][0]

int64_cols = ['nrr_num', 'nrr_den', 'nrr_canon_num', 'nrr_canon_den']
for c in st_table['columns']:
    if c['name'] in int64_cols:
        c['dataType'] = 'int64'
        print(f"Updated {c['name']} dataType to int64")

# Check if group_display column exists, if not add it
col_names = [c['name'] for c in st_table['columns']]
if 'group_display' not in col_names:
    st_table['columns'].append({
        "name": "group_display",
        "dataType": "string",
        "isDataTypeInferred": True,
        "type": "calculated",
        "expression": 'IF(view_tournament_standings[stage_normalized] = "Super 8", "Super 8 - Group " & view_tournament_standings[group_name], "Group " & view_tournament_standings[group_name])'
    })
    print("Added calculated column group_display")

# Update partition M expression in model.bim
m_expr = [
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
    "        {\"nrr_num\", Int64.Type},\n",
    "        {\"nrr_den\", Int64.Type},\n",
    "        {\"nrr_canon_num\", Int64.Type},\n",
    "        {\"nrr_canon_den\", Int64.Type}\n",
    "    })\n",
    "in\n",
    "    #\"Changed Type\"\n"
]
st_table['partitions'][0]['source']['expression'] = m_expr
print("Updated partition M expression in model.bim")

with open(BIM_PATH, 'w', encoding='utf-8') as f:
    json.dump(bim, f, indent=2)
print("Saved model.bim")

# 2. Update power_query_m_code.m
with open(M_PATH, 'r', encoding='utf-8') as f:
    m_code = f.read()

# Replace the view_tournament_standings block in m_code
m_new_block = """// Table: view_tournament_standings
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
        {"nrr_num", Int64.Type},
        {"nrr_den", Int64.Type},
        {"nrr_canon_num", Int64.Type},
        {"nrr_canon_den", Int64.Type}
    })
in
    #"Changed Type"
"""

if "// Table: view_tournament_standings" in m_code:
    idx = m_code.find("// Table: view_tournament_standings")
    m_code_updated = m_code[:idx].rstrip() + "\n\n" + m_new_block
else:
    m_code_updated = m_code + "\n\n" + m_new_block

with open(M_PATH, 'w', encoding='utf-8') as f:
    f.write(m_code_updated)
print("Updated power_query_m_code.m")

# 3. Update report.json for FIX 2 Slicer UX
with open(REPORT_PATH, 'r', encoding='utf-8') as f:
    rep = json.load(f)

sec2 = [s for s in rep['sections'] if s['name'] == 'ReportSection_Page2_Standings'][0]

# Update Slicer 2 (Group Slicer) to use hierarchical/contextual group_display
# Find slicer vc
for vc in sec2['visualContainers']:
    cfg = json.loads(vc['config'])
    name = cfg.get('name')
    if name == 'Slicer_Group_Standings':
        # Option A: Hierarchical slicer projecting stage and group_display
        cfg['singleVisual']['projections'] = {
            "Values": [
                {"queryRef": "view_tournament_standings.stage_normalized"},
                {"queryRef": "view_tournament_standings.group_display"}
            ]
        }
        cfg['singleVisual']['objects'] = {
            "general": [{
                "properties": {
                    "orientation": {"expr": {"Literal": {"Value": "'vertical'"}}}
                }
            }],
            "header": [{
                "properties": {
                    "show": {"expr": {"Literal": {"Value": "true"}}},
                    "title": {"expr": {"Literal": {"Value": "'Stage & Group Filter (Hierarchical)'"}}}
                }
            }]
        }
        vc['config'] = json.dumps(cfg)
        print("Updated Slicer_Group_Standings to Hierarchical Option A")
    elif name == 'Matrix_TournamentStandings':
        # Also include group_display in matrix hierarchy or tooltips
        projections = cfg['singleVisual']['projections']
        # Ensure matrix sorts points DESC, then raw rational NRR (nrr_canon_num / nrr_canon_den) DESC, then pool_rank ASC
        cfg['singleVisual']['sortDefinition'] = {
            "sort": [
                {"field": {"queryRef": "view_tournament_standings.points"}, "direction": "Descending"},
                {"field": {"queryRef": "view_tournament_standings.pool_rank"}, "direction": "Ascending"},
                {"field": {"queryRef": "view_tournament_standings.team_name"}, "direction": "Ascending"}
            ]
        }
        vc['config'] = json.dumps(cfg)
        print("Updated Matrix sort definition")

with open(REPORT_PATH, 'w', encoding='utf-8') as f:
    json.dump(rep, f, indent=2)
print("Saved report.json")
