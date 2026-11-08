#!/usr/bin/env python3
"""Release identity incorporates source SHA, lockfile SHA, actual builder files, and revision."""
import argparse,hashlib,json,os,re,sys
from pathlib import Path

def identity(root,record,revision):
    if not re.fullmatch(r'r[1-9][0-9]*',revision):raise ValueError('Builder revision must be r1, r2, ...')
    root=Path(root).resolve();r=json.loads(Path(record).read_text(encoding='utf-8'))
    digest=hashlib.sha256()
    paths=[]
    for sub in ('scripts','launcher','.github/workflows','tests'):
        paths.extend(p for p in (root/sub).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    for p in sorted(paths):
        digest.update(p.relative_to(root).as_posix().encode('utf-8'));digest.update(b'\0');digest.update(p.read_bytes())
    code=digest.hexdigest()
    release_tag=f'portable-v{r["version"]}-{r["commit"][:8]}-{r["lock_sha256"][:8]}-{code[:8]}-{revision}'
    r['builder_code_sha256']=code;r['builder_revision']=revision;r['release_tag']=release_tag
    return r
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--identity',required=True)
    p.add_argument('--revision',required=True);args=p.parse_args()
    try:
        r=identity(args.root,args.identity,args.revision)
        Path(args.identity).write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
        print('RELEASE IDENTITY',r['release_tag'])
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as out:
                out.write(f'tag={r["release_tag"]}\n')
    except Exception as exc:print('ERROR: '+str(exc),file=sys.stderr);sys.exit(1)
