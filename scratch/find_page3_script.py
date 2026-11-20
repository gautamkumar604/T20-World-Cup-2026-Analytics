import os

for root, dirs, files in os.walk('scratch'):
    for f in files:
        if f.endswith('.py'):
            p = os.path.join(root, f)
            with open(p, 'r', encoding='utf-8') as fp:
                t = fp.read()
                if 'sections' in t and 'ReportSection_Page3' in t:
                    print('Found Page 3 section in:', p)
