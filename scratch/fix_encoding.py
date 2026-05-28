import os
path = 'c:/IA_dublagem/nexus_core.py'
try:
    # Tenta ler com várias codificações comuns em Windows
    content = None
    for enc in ['utf-8-sig', 'utf-16', 'latin-1']:
        try:
            with open(path, 'r', encoding=enc) as f:
                content = f.read()
            break
        except:
            continue
    
    if content:
        # Salva como UTF-8 puro
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print('SUCCESS')
    else:
        print('FAILED_TO_READ')
except Exception as e:
    print(f'ERROR: {e}')
