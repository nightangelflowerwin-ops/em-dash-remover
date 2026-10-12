"""CI helper: push reviewed-file changes to a new branch and open a pull request."""
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request


def publish(root, report, repository, token, run_id, request=None):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):
        raise ValueError('Expected owner/repository')
    if not re.fullmatch(r'[0-9]+',run_id):raise ValueError('Expected numeric workflow run ID')
    if report['errors']:raise ValueError('Resolve scanner errors before creating a pull request')
    files=[item['path'] for item in report['files'] if item['written']]
    if not files:return None
    if request is None:
        def request(path, method='GET', body=None):
            req=urllib.request.Request('https://api.github.com'+path,
                data=json.dumps(body).encode() if body is not None else None,method=method,
                headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'em-dash-remover'})
            with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
    base='/repos/'+repository
    default=request(base)['default_branch']
    for page in range(1,101):
        prs=request(base+'/pulls?state=open&per_page=100&page='+str(page))
        for pr in prs:
            if pr['head']['ref'].startswith('automation/em-dash-remover-') and pr['base']['ref']==default and (pr['head'].get('repo') or {}).get('full_name')==repository:
                return pr['html_url']
        if len(prs)<100:break
    else:raise ValueError('Pull-request pagination limit reached')
    def git(*args):
        return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.STDOUT).decode()
    if git('branch','--show-current').strip()!=default:
        raise ValueError('Cleanup must start from the checked-out default branch')
    branch='automation/em-dash-remover-'+run_id
    git('switch','-c',branch)
    git('--literal-pathspecs','add','--',*files)
    staged=set(git('diff','--cached','--name-only','-z').split('\0'))-{''}
    if not staged.issubset(set(files)):
        raise ValueError('Unrelated staged changes found; use a clean checkout')
    if not git('diff','--cached','--name-only'):return None
    git('-c','user.name=github-actions[bot]','-c','user.email=41898282+github-actions[bot]@users.noreply.github.com',
        'commit','-m','Replace em dashes in repository text')
    git('push','origin',branch)
    body={'title':'Replace em dashes in repository text','head':branch,'base':default,
          'body':f"Proposes {report['replacements']} replacements in {len(files)} tracked files. Review the diff before merging. No history was rewritten. Scanner defaults to documentation; source/data changes require an explicit opt-in."}
    try:return request(base+'/pulls','POST',body)['html_url']
    except urllib.error.HTTPError as error:
        if error.code==403:
            raise RuntimeError('Branch pushed, but PR creation was denied. Check repository Settings > Actions > General and allow GitHub Actions to create pull requests, or open a PR from the cleanup branch manually.') from None
        raise


if __name__=='__main__':
    if not os.environ.get('GH_TOKEN'):raise SystemExit('A repository token is required to propose a pull request')
    report=json.loads(Path(os.environ.get('ED_REPORT','emdash-report.json')).read_text(encoding='utf-8'))
    result=publish(Path(os.environ.get('ED_ROOT','.')),report,os.environ['GITHUB_REPOSITORY'],os.environ['GH_TOKEN'],os.environ['GITHUB_RUN_ID'])
    print(result or 'No changes to propose')
    if result and os.environ.get('GITHUB_OUTPUT'):
        if not result.startswith('https://github.com/') or '\n' in result:raise SystemExit('Unexpected pull-request URL')
        with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as handle:handle.write('pr-url='+result+'\n')
