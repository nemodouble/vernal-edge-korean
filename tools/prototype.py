"""Local technical gate only; never package private/original or private/build."""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import shutil
from build_locale import ROOT, load

GAME=ROOT.parent
STATE=ROOT/'private/prototype-state.json'

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

def stopped():
    class Entry(ctypes.Structure):
        _fields_=[('dwSize',wintypes.DWORD),('cntUsage',wintypes.DWORD),
            ('th32ProcessID',wintypes.DWORD),('th32DefaultHeapID',ctypes.c_size_t),
            ('th32ModuleID',wintypes.DWORD),('cntThreads',wintypes.DWORD),
            ('th32ParentProcessID',wintypes.DWORD),('pcPriClassBase',wintypes.LONG),
            ('dwFlags',wintypes.DWORD),('szExeFile',wintypes.WCHAR*260)]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes=[wintypes.DWORD,wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype=wintypes.HANDLE
    kernel.Process32FirstW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)]
    kernel.Process32NextW.argtypes=[wintypes.HANDLE,ctypes.POINTER(Entry)]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.CreateToolhelp32Snapshot(2,0)
    if handle == ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry=Entry();entry.dwSize=ctypes.sizeof(entry)
        more=kernel.Process32FirstW(handle,ctypes.byref(entry))
        if not more:raise ctypes.WinError(ctypes.get_last_error())
        while more:
            if entry.szExeFile.lower()=='vernaledge.exe':
                raise RuntimeError('Close Vernal Edge before applying or restoring the prototype.')
            more=kernel.Process32NextW(handle,ctypes.byref(entry))
        if ctypes.get_last_error()!=18:raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.CloseHandle(handle)

def apply():
    stopped()
    if STATE.exists():raise RuntimeError('A prototype is already installed. Restore it first.')
    mode=load(ROOT/'private/build/locale-mode.json')
    report=load(ROOT/'private/build/validation.json')
    if report['errors']:raise RuntimeError('Static validation failed.')
    manifest=load(ROOT/'private/original/manifest.json')
    names=['data.win','loc/available.json','loc/'+mode['locale']]
    state={'phase':'preparing','mode':mode['mode'],'files':[]}
    for name in names:
        target=GAME/name;original=manifest['files'].get(name)
        expected=original['sha256'] if original else None
        if digest(target)!=expected:raise RuntimeError('Target differs from supported original: '+name)
        source=ROOT/'private/build'/name
        stage=target.with_name(target.name+'.ko-stage')
        if stage.exists():raise RuntimeError('Unexpected staging file: '+str(stage))
        shutil.copy2(source,stage)
        patched=digest(stage)
        if patched!=digest(source):raise RuntimeError('Staged file checksum mismatch')
        state['files'].append({'path':name,'original':expected,'patched':patched})
    STATE.write_text(json.dumps(state,indent=2),encoding='utf-8')
    try:
        state['phase']='committing';STATE.write_text(json.dumps(state,indent=2),encoding='utf-8')
        for row in state['files']:
            target=GAME/row['path'];os.replace(target.with_name(target.name+'.ko-stage'),target)
        state['phase']='installed';STATE.write_text(json.dumps(state,indent=2),encoding='utf-8')
    except BaseException:
        restore(allow_partial=True)
        raise
    print('Prototype installed; no save files were accessed. mode='+mode['mode'])

def restore(allow_partial=False):
    stopped()
    if not STATE.exists():raise RuntimeError('No prototype state found.')
    state=load(STATE)
    # Validate every file before changing any file; preserve user modifications.
    for row in state['files']:
        actual=digest(GAME/row['path'])
        if actual not in (row['patched'],row['original']):raise RuntimeError('Conflict; refusing to overwrite: '+row['path'])
        if row['original'] and digest(ROOT/'private/original'/row['path'])!=row['original']:
            raise RuntimeError('Original backup checksum mismatch')
    for row in reversed(state['files']):
        target=GAME/row['path']
        if row['original']:
            temp=target.with_name(target.name+'.ko-restore')
            shutil.copy2(ROOT/'private/original'/row['path'],temp);os.replace(temp,target)
        elif target.exists():target.unlink()
        stage=target.with_name(target.name+'.ko-stage')
        if stage.exists():stage.unlink()
    STATE.rename(STATE.with_name('prototype-state.last-restored.json')) if not STATE.with_name('prototype-state.last-restored.json').exists() else STATE.unlink()
    print('Original game files restored and hashes verified.')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['apply','restore'])
    args=parser.parse_args();apply() if args.action=='apply' else restore()
