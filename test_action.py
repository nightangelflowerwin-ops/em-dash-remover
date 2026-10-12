import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from action_entry import arguments
from emdash import scan
from open_pr import publish


class ActionTests(unittest.TestCase):
    def test_inputs_are_literal_arguments(self):
        value='$(echo secret); anything'
        args=arguments({'ED_ROOT':value,'ED_ALL':'true','ED_EXCLUDE':'vendor/*\n*.min.js'})
        self.assertIn(value,args)
        self.assertIn('--all-text',args)
        self.assertEqual(args.count('--exclude'),2)
        with self.assertRaises(ValueError):arguments({'ED_ALL':'yes'})

    def test_real_git_branch_commit_push_and_pr_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'repo';remote=Path(directory)/'remote.git'
            subprocess.run(['git','init','-q','--bare',str(remote)],check=True)
            subprocess.run(['git','init','-q','-b','main',str(root)],check=True)
            def git(*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.STDOUT).decode().strip()
            path=root/'README.md';path.write_text('a'+chr(8212)+'b',encoding='utf-8')
            git('add','.');git('-c','user.name=Test','-c','user.email=test@example.com','commit','-m','fixture')
            git('remote','add','origin',str(remote));git('push','origin','main')
            report=scan(root,fix=True);posted=[]
            def api(path,method='GET',body=None):
                if method=='POST':posted.append(body);return {'html_url':'https://github.com/test/repo/pull/1'}
                return [] if '/pulls?' in path else {'default_branch':'main'}
            url=publish(root,report,'test/repo','unused','123',api)
            self.assertEqual(url,'https://github.com/test/repo/pull/1')
            self.assertEqual(posted[0]['base'],'main')
            data=subprocess.check_output(['git','--git-dir',str(remote),'show','automation/em-dash-remover-123:README.md'])
            self.assertEqual(data,b'a-b')
            self.assertIsNone(publish(root,{'errors':[],'files':[]},'test/repo','unused','123',api))


if __name__=='__main__':unittest.main()
