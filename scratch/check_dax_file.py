with open('power_bi/dax_measures.dax', 'r', encoding='utf-8') as f:
    text = f.read()

print('Length of dax_measures.dax:', len(text))
for line in text.splitlines():
    if '=' in line and not line.strip().startswith('//') and not line.strip().startswith('--'):
        print(line[:80])
