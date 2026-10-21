"""Fetch pinned, official development inputs and preserve the original game."""
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT.parent
BACKUP = ROOT / 'private' / 'original'
VENDOR = ROOT / 'private' / 'vendor'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def initialize():
    BACKUP.mkdir(parents=True, exist_ok=True)
    expected = {'data.win': '71fef9792ffbfba2112fdbd0515bc4cdcb4ce6e75d2043b6cfebd5f54e7158a4',
                'VernalEdge.exe': 'ef2f48ce689de6a6629aa6884dffa3d22504edc052bee4aaad3a83fae90783ff'}
    paths = ['data.win', 'VernalEdge.exe'] + [str(p.relative_to(GAME)).replace('\\', '/') for p in (GAME/'loc').glob('*.json')]
    manifest = {'appid': 1546710, 'buildid': '10939741', 'files': {}}
    for name in paths:
        source, target = GAME/name, BACKUP/name
        if name in expected and sha(source) != expected[name]:
            raise RuntimeError('Unsupported original: ' + name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if sha(target) != sha(source):
                raise RuntimeError('Refusing to replace original backup: ' + name)
        else:
            shutil.copy2(source, target)
        manifest['files'][name] = {'sha256': sha(target), 'size': target.stat().st_size}
    (BACKUP/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Original files verified and backed up.', flush=True)

def download(url, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        return
    request = urllib.request.Request(url, headers={'User-Agent': 'VernalEdge-Korean-Patch'})
    with urllib.request.urlopen(request, timeout=90) as response, target.open('wb') as output:
        shutil.copyfileobj(response, output)
    print(target.name, target.stat().st_size, sha(target), flush=True)

def fetch():
    urls = {
      'utmt.zip': 'https://github.com/UnderminersTeam/UndertaleModTool/releases/download/0.9.2.0/UTMT_CLI_v0.9.2.0-Windows.zip',
      'galmuri.zip': 'https://github.com/quiple/galmuri/releases/download/v2.40.4/Galmuri-v2.40.4.zip',
      'ImportGMS2FontData.csx': 'https://raw.githubusercontent.com/UnderminersTeam/UndertaleModTool/0.9.2.0/UndertaleModTool/Scripts/Resource%20Importers/ImportGMS2FontData.csx',
    }
    for name, url in urls.items():
        try:
            download(url, VENDOR/name)
        except Exception as error:
            if not name.endswith('.csx'):
                raise
            print(name, error, flush=True)
    for name, folder in [('utmt.zip', 'utmt'), ('galmuri.zip', 'galmuri')]:
        dest = VENDOR/folder
        if not dest.exists():
            with zipfile.ZipFile(VENDOR/name) as archive:
                archive.extractall(dest)
    (VENDOR/'sources.json').write_text(json.dumps({name: {'url':url, 'sha256':sha(VENDOR/name)} for name,url in urls.items() if (VENDOR/name).exists()}, indent=2), encoding='utf-8')

if __name__ == '__main__':
    import sys
    if '--fetch' in sys.argv:
        fetch()
    else:
        initialize()
