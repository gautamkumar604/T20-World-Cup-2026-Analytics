with open('scratch/apply_phase4_2.py', 'r', encoding='utf-8') as f:
    text = f.read()

pos = text.find('ReportSection_Page3')
print(text[pos-200:pos+1500])
