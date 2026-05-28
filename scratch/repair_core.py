import os

core_path = r'c:\IA_dublagem\nexus_core.py'
opt_path = r'c:\IA_dublagem\nexus_core.py_optimized_end.py'

with open(core_path, 'r', encoding='utf-8') as f:
    content = f.read()

marker = 'def transcrever_e_diarizar'
idx = content.find(marker)

if idx != -1:
    with open(opt_path, 'r', encoding='utf-8') as f:
        optimized_part = f.read()
    
    final_content = content[:idx] + optimized_part
    
    with open(core_path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    print("SUCCESS: nexus_core.py optimized and cleaned.")
else:
    print("ERROR: Marker not found.")
