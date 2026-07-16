with open("c:/IA_dublagem/nexus/client/aider_dashboard.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

in_style = False
in_script = False
style_start = -1
script_start = -1

for idx, line in enumerate(lines):
    if "<style" in line:
        print(f"Style starts at line {idx+1}: {line.strip()}")
    if "</style>" in line:
        print(f"Style ends at line {idx+1}: {line.strip()}")
    if "<script" in line and "src=" not in line:
        print(f"Script starts at line {idx+1}: {line.strip()}")
    if "</script>" in line:
        print(f"Script ends at line {idx+1}: {line.strip()}")
