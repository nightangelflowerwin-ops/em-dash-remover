import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from emdash import replace, scan, main


class RemoverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(['git','init','-q',str(self.root)],check=True)

    def file(self,name,data):
        path=self.root/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(data)
        subprocess.run(['git','-C',str(self.root),'add','--',name],check=True)
        return path

    def test_check_fix_idempotence_and_preserved_crlf(self):
        original=('Hello '+chr(8212)+' world\r\n').encode()
        path=self.file('README.md',original)
        self.assertEqual(scan(self.root)['replacements'],1)
        self.assertEqual(path.read_bytes(),original)
        self.assertEqual(scan(self.root,fix=True)['changed_files'],1)
        self.assertEqual(path.read_bytes(),b'Hello - world\r\n')
        self.assertEqual(scan(self.root,fix=True)['changed_files'],0)

    def test_encoded_variants_and_literal_replacement(self):
        code=format(8212,'04x')
        values=['\\u'+code,'\\\\u'+code,'&#'+str(8212)+';','&#x'+code,'&amp;mdash;',chr(226)+chr(8364)+chr(8221)]
        for value in values:
            self.assertEqual(replace(value,encoded=True),('-',1))
        self.assertEqual(replace('&#x'+code+'f;',encoded=True)[1],0)
        self.assertEqual(replace(chr(8212),replacement='\\1')[0],'\\1')

    def test_scope_exclusions_binary_and_untracked(self):
        dash=chr(8212).encode()
        self.file('main.py',dash)
        self.file('skip.md',dash)
        self.file('image.png',dash)
        (self.root/'untracked.md').write_bytes(dash)
        report=scan(self.root,fix=True,excludes=['skip.md'])
        self.assertEqual(report['changed_files'],0)
        report=scan(self.root,fix=True,all_text=True,excludes=['skip.md'])
        self.assertEqual(report['changed_files'],1)
        self.assertEqual((self.root/'image.png').read_bytes(),dash)

    def test_utf16_size_limit_and_json(self):
        self.file('utf16.txt',b'\xff\xfe'+('x'+chr(8212)).encode('utf-16-le'))
        value=json.dumps({'text':chr(8212)})
        path=self.file('data.json',value.encode())
        report=scan(self.root,fix=True,all_text=True,encoded=True)
        self.assertEqual(report['replacements'],2)
        self.assertEqual(json.loads(path.read_text())['text'],'-')
        self.assertEqual((self.root/'utf16.txt').read_bytes(),b'\xff\xfe'+b'x\0-\0')
        self.assertEqual(scan(self.root,max_bytes=1)['scanned'],0)

    def test_symlink_does_not_edit_outside_file(self):
        with tempfile.TemporaryDirectory() as other:
            outside=Path(other)/'outside.md';outside.write_text(chr(8212),encoding='utf-8')
            try:(self.root/'link.md').symlink_to(outside)
            except OSError:self.skipTest('Symlink creation unavailable')
            subprocess.run(['git','-C',str(self.root),'add','link.md'],check=True)
            self.assertEqual(scan(self.root,fix=True)['changed_files'],0)
            self.assertEqual(outside.read_text(encoding='utf-8'),chr(8212))

    def test_cli_exit_codes(self):
        self.file('a.md',chr(8212).encode())
        self.assertEqual(main(['--root',str(self.root)]),1)
        self.assertEqual(main(['--root',str(self.root),'--mode','fix']),0)
        self.assertEqual(main(['--root',str(self.root)]),0)


if __name__=='__main__':unittest.main()
