import zipfile

with zipfile.ZipFile('power_bi/T20_World_Cup_2026_Analytics.pbit', 'r') as z:
    for name in z.namelist():
        info = z.getinfo(name)
        print(f"{name} ({info.file_size} bytes)")
