"""End-to-end PowerShell 5.1 install/recovery tests against synthetic fixtures."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from package import delta, sha, reconstruct

TESTROOT=ROOT/'private/tests'/uuid.uuid4().hex
POWERSHELL=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'

class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.root=TESTROOT/self._testMethodName
        self.game=self.root/'game';self.package=self.root/'package'
        (self.game/'loc').mkdir(parents=True)
        (self.package/'payload').mkdir(parents=True)
        self.original={'data.win':b'HEADER'+b'A'*5000+b'ORIGINAL'+b'Z'*5000,
                       'loc/available.json':b'[{"code":"en-US"}]'}
        self.patched={'data.win':b'HEADER'+b'A'*5000+b'KOREAN_FONT'+b'Z'*5000,
                      'loc/available.json':b'[{"code":"en-US"},{"code":"ko-KR"}]',
                      'loc/ko-KR.json':'{"Use":"사용"}'.encode('utf-8')}
        self.exe=b'Synthetic test executable guard - never execute'
        (self.game/'VernalEdge.exe').write_bytes(self.exe)
        for name,raw in self.original.items():(self.game/name).write_bytes(raw)
        self.manifest=dict(format=1,package='synthetic-test',appid=1546710,buildid='10939741',
            exe=sha(self.exe),releaseReady=False,files=[])
        for name,raw in self.patched.items():
            before=self.original.get(name,b'')
            ops=delta(before,raw,self.package/'payload')
            self.assertEqual(reconstruct(before,ops,self.package/'payload'),raw)
            self.manifest['files'].append(dict(path=name,original=sha(before) if name in self.original else None,
                patched=sha(raw),size=len(raw),operations=ops))
        self.write_manifest()

    def write_manifest(self):
        (self.package/'manifest.json').write_text(json.dumps(self.manifest),encoding='utf-8')

    def run_patch(self,mode='Install',scenario='normal',success=True):
        result=subprocess.run([str(POWERSHELL),'-NoProfile','-NonInteractive','-File',
            str(ROOT/'tests/installer_driver.ps1'),'-Game',str(self.game),'-Package',str(self.package),
            '-Mode',mode,'-Scenario',scenario],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=60)
        if success:self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        else:self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
        return result.stdout+result.stderr

    def assert_original(self):
        for name,raw in self.original.items():self.assertEqual((self.game/name).read_bytes(),raw)
        self.assertFalse((self.game/'loc/ko-KR.json').exists())
        self.assertEqual((self.game/'VernalEdge.exe').read_bytes(),self.exe)

    def state_path(self):return self.game/'.vernal-edge-ko-backup/state.json'

    def test_install_verify_reinstall_remove(self):
        self.run_patch()
        for name,raw in self.patched.items():self.assertEqual((self.game/name).read_bytes(),raw)
        self.run_patch('Verify');self.assertIn('already installed',self.run_patch())
        before=(self.game/'.vernal-edge-ko-backup/data.win').read_bytes()
        self.run_patch('Uninstall');self.assert_original()
        self.run_patch();self.run_patch('Uninstall');self.assert_original()
        self.assertEqual((self.game/'.vernal-edge-ko-backup/data.win').read_bytes(),before)

    def test_wrong_original(self):
        (self.game/'data.win').write_bytes(b'user changed')
        self.assertIn('Unsupported original',self.run_patch(success=False))
        self.assertEqual((self.game/'data.win').read_bytes(),b'user changed')
        self.assertFalse(self.state_path().exists())

    def test_wrong_executable(self):
        (self.game/'VernalEdge.exe').write_bytes(b'new build')
        self.assertIn('Unsupported executable',self.run_patch(success=False))
        self.assertEqual((self.game/'data.win').read_bytes(),self.original['data.win'])

    def test_existing_korean_file(self):
        (self.game/'loc/ko-KR.json').write_bytes(b'user translation')
        self.run_patch(success=False)
        self.assertEqual((self.game/'loc/ko-KR.json').read_bytes(),b'user translation')
        self.assertEqual((self.game/'data.win').read_bytes(),self.original['data.win'])

    def test_corrupt_payload_precommit(self):
        next((self.package/'payload').glob('*.gz')).write_bytes(b'corrupt')
        self.assertIn('payload checksum mismatch',self.run_patch(success=False))
        self.assert_original()

    def test_user_change_blocks_entire_removal(self):
        self.run_patch()
        (self.game/'loc/available.json').write_bytes(b'user modification')
        self.assertIn('Conflict',self.run_patch('Uninstall',success=False))
        self.assertEqual((self.game/'data.win').read_bytes(),self.patched['data.win'])
        self.assertEqual((self.game/'loc/available.json').read_bytes(),b'user modification')

    def test_corrupt_backup_blocks_removal(self):
        self.run_patch()
        (self.game/'.vernal-edge-ko-backup/data.win').write_bytes(b'corrupt')
        self.assertIn('backup is missing or corrupt',self.run_patch('Uninstall',success=False))
        for name,raw in self.patched.items():self.assertEqual((self.game/name).read_bytes(),raw)

    def test_partial_commit_recovery(self):
        self.run_patch()
        state=json.loads(self.state_path().read_text(encoding='utf-8-sig'))
        state['phase']='installing';self.state_path().write_text(json.dumps(state),encoding='utf-8')
        (self.game/'loc/available.json').write_bytes(self.original['loc/available.json'])
        (self.game/'loc/ko-KR.json').unlink()
        self.assertIn('incomplete',self.run_patch(success=False))
        self.run_patch('Uninstall');self.assert_original()

    def test_commit_failure_rolls_back(self):
        self.assertIn('original files restored',self.run_patch(scenario='fail-second-commit',success=False))
        self.assert_original()
        self.assertEqual(json.loads(self.state_path().read_text())['phase'],'removed')

    def test_running_game_guard(self):
        self.assertIn('Close Vernal Edge',self.run_patch(scenario='running',success=False))
        self.assert_original();self.assertFalse(self.state_path().exists())

    def test_path_traversal_rejected(self):
        self.manifest['files'][0]['path']='../escape'
        self.write_manifest()
        self.assertIn('Invalid patch target',self.run_patch(success=False))
        self.assert_original()

    def test_invalid_copy_range_rejected(self):
        self.manifest['files'][0]['operations'][0]['offset']=-1
        self.write_manifest()
        self.assertIn('source range is invalid',self.run_patch(success=False))
        self.assert_original()

if __name__=='__main__':
    unittest.main(verbosity=2)
