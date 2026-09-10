"""Cliente de publicação: usa o gerenciador Git sem gravar/exibir credenciais."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import requests

REPO = 'NarraVox/PhoenixDub-AI'


def session():
    result = subprocess.run(['git','credential','fill'], input='protocol=https\nhost=github.com\n\n',
                            text=True, capture_output=True, env={**os.environ, 'GIT_TERMINAL_PROMPT':'0'})
    values = dict(line.split('=',1) for line in result.stdout.splitlines() if '=' in line)
    if result.returncode or not values.get('password'):
        raise RuntimeError('Autentique o Git Credential Manager antes de publicar.')
    client = requests.Session()
    client.headers.update({'Authorization':'Bearer '+values['password'], 'Accept':'application/vnd.github+json'})
    return client


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('method', choices=['get','post','patch'])
    parser.add_argument('endpoint', help='Caminho relativo ao repositório, por exemplo actions/runs')
    parser.add_argument('--body', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if '..' in args.endpoint or args.endpoint.startswith('/'):
        raise ValueError('Endpoint inválido.')
    client = session()
    body = json.loads(args.body.read_text(encoding='utf-8')) if args.body else None
    response = client.request(args.method, f'https://api.github.com/repos/{REPO}/{args.endpoint}', json=body, timeout=60)
    if not response.ok:
        raise RuntimeError(f'GitHub retornou HTTP {response.status_code}: {response.text[:500]}')
    if args.output:
        args.output.write_bytes(response.content)
        print(f'Resposta salva em {args.output}')
    elif response.content:
        data=response.json()
        if 'workflow_runs' in data:
            data=[{k:r.get(k) for k in ('id','head_sha','status','conclusion','html_url','event')} for r in data['workflow_runs']]
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print('GitHub: operação aceita.')
