"""Exercise the actual shipped delta/installer on a private copy, never live saves."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid
import zipfile
from build_locale import ROOT,load
from package import PACKAGE,sha

def main():
    package=ROOT/'dist'/PACKAGE
    manifest=load(package/'manifest.json')
    scratch=ROOT/'private/package-smoke'/uuid.uuid4().hex
    game=scratch/'game';(game/'loc').mkdir(parents=True)
    if shutil.disk_usage(game).free<1_200_000_000:raise RuntimeError('Not enough free space for independent install test')
    names=['data.win','VernalEdge.exe','loc/available.json']
    originals={}
    for name in names:
        shutil.copy2(ROOT/'private/original'/name,game/name)
        originals[name]=sha((game/name).read_bytes())
    powershell=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
    results=[]
    for mode in ['Install','Verify','Uninstall']:
        command=[str(powershell),'-NoProfile','-NonInteractive','-File',str(ROOT/'tests/installer_driver.ps1'),
            '-Game',str(game),'-Package',str(package),'-ModulePath',str(package/'Patch.Core.psm1'),'-Mode',mode]
        proc=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
        print(mode,proc.returncode,proc.stdout.strip(),flush=True)
        results.append(dict(mode=mode,exitcode=proc.returncode,output=proc.stdout.strip()))
        if proc.returncode:raise RuntimeError(proc.stdout+proc.stderr)
    after={name:sha((game/name).read_bytes()) for name in names}
    assert originals==after
    assert not (game/'loc/ko-KR.json').exists()
    archive=package.parent/(PACKAGE+'.zip')
    with zipfile.ZipFile(archive) as zipped:
        entries=zipped.namelist()
        assert not any(Path(name).name.lower() in ('data.win','vernaledge.exe') or name.lower().endswith(('.exe','.dll')) or '/private/' in name.lower() for name in entries)
    report=dict(package=PACKAGE,windows_powershell='5.1',synthetic_installer_tests_passed=12,
        actual_package_steps=results,original_hashes=originals,restored_hashes=after,
        added_locale_removed=True,no_original_executable_or_game_bundle_in_zip=True,
        archive_bytes=archive.stat().st_size,archive_sha256=sha(archive.read_bytes()),
        release_ready=False,manual_qa='Initial prototype only; full beta gameplay review pending')
    dest=ROOT/'private/build/package-smoke.json'
    dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Actual package install/verify/uninstall restored original hashes exactly.',flush=True)
    # Explicit generated files only; leave any unexpected files alone.
    backup=game/'.vernal-edge-ko-backup'
    cleanup=[game/name for name in names]+[backup/'data.win',backup/'loc/available.json',backup/'state.json']
    for file in cleanup:
        assert file.resolve().is_relative_to(scratch.resolve())
        if file.is_file():file.unlink()
    for folder in [backup/'loc',backup,game/'loc',game,scratch]:
        assert folder.resolve().is_relative_to((ROOT/'private/package-smoke').resolve())
        if folder.exists() and not list(folder.iterdir()):folder.rmdir()

if __name__=='__main__':main()
