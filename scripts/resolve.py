#!/usr/bin/env python3
"""Select an exact stable bankjaneo/caprine release and verify its Git tag."""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys, urllib.error, urllib.request
from pathlib import Path
REPO = 'bankjaneo/caprine'
TAG = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)$')

def api(url: str) -> object:
    headers = {'Accept':'application/vnd.github+json','User-Agent':'CaprinePortableBuilder-r1','X-GitHub-Api-Version':'2022-11-28'}
    if os.environ.get('GH_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GH_TOKEN']
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=40) as reply:
            return json.load(reply)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise RuntimeError('Official upstream release API unavailable (404); refusing fallback to main') from error
        raise RuntimeError(f'GitHub API HTTP {error.code}: {error.read(250)!r}') from error

def git(*args: str) -> str:
    cp = subprocess.run(['git', *args],capture_output=True,text=True,encoding='utf-8',check=False,timeout=120)
    if cp.returncode: raise RuntimeError('git ' + ' '.join(args) + ': ' + cp.stderr.strip())
    return cp.stdout

def resolve(requested: str, repo_path: Path):
    releases = []
    page=1
    while True:
        batch = api(f'https://api.github.com/repos/{REPO}/releases?per_page=100&page={page}')
        if not isinstance(batch,list): raise RuntimeError('Unexpected GitHub releases payload')
        releases.extend(batch)
        if len(batch)<100: break
        if page>=5: raise RuntimeError('Too many releases: refusing partial pagination')
        page+=1
    candidates=[]
    for r in releases:
        tag = r.get('tag_name','')
        match=TAG.fullmatch(tag)
        if match and not r.get('draft') and not r.get('prerelease') and r.get('published_at'):
            candidates.append((tuple(map(int,match.groups())),tag))
    if not candidates: raise RuntimeError('No stable tagged upstream release found')
    candidates.sort(key=lambda row:row[0],reverse=True)
    if requested.strip().lower() in ('','latest'):
        version,tag=candidates[0]
    else:
        match=TAG.fullmatch(requested.strip())
        if not match: raise RuntimeError('Requested version must be stable x.y.z or vx.y.z')
        matching=[(v,t) for v,t in candidates if v==tuple(map(int,match.groups()))]
        if not matching: raise RuntimeError(f'{requested} is not a published non-prerelease release')
        version,tag=matching[0]
    # An annotated Git tag advertises a peeled ^{} reference; lightweight tags do not.
    remote=f'https://github.com/{REPO}.git'
    listing=git('ls-remote','--tags',remote, f'refs/tags/{tag}',f'refs/tags/{tag}^{{}}')
    sha_by_ref={ref:sha for sha,ref in (line.split('\t',1) for line in listing.splitlines() if '\t' in line)}
    sha=sha_by_ref.get(f'refs/tags/{tag}^{{}}') or sha_by_ref.get(f'refs/tags/{tag}')
    if not sha or not re.fullmatch('[0-9a-f]{40}',sha): raise RuntimeError('Could not resolve immutable commit for upstream tag')
    repo_path.parent.mkdir(parents=True,exist_ok=True)
    git('clone','--no-checkout','--filter=blob:none',remote,str(repo_path))
    git('-C',str(repo_path),'fetch','--depth','1','origin',tag)
    git('-C',str(repo_path),'checkout','--detach',sha)
    actual=git('-C',str(repo_path),'rev-parse','HEAD').strip()
    if actual!=sha: raise RuntimeError(f'Checkout SHA mismatch {actual} != {sha}')
    package=json.loads((repo_path/'package.json').read_text(encoding='utf-8'))
    resolved='.'.join(str(n) for n in version)
    if package['version']!=resolved: raise RuntimeError(f'Package version {package["version"]} != tag version {resolved}')
    lock=repo_path/'package-lock.json'
    if not lock.is_file(): raise RuntimeError('Missing upstream npm package-lock.json')
    import hashlib
    locksha=hashlib.sha256(lock.read_bytes()).hexdigest()
    return dict(tag=tag,version=resolved,commit=sha,lock_sha256=locksha,repo=REPO)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--version',default='latest'); p.add_argument('--clone',required=True);p.add_argument('--out',required=True)
    args=p.parse_args()
    try:
        ident=resolve(args.version,Path(args.clone).resolve())
        dest=Path(args.out);dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(ident,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(ident,indent=2))
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as out:
                for key,value in ident.items():out.write(f'{key}={value}\n')
    except Exception as exc:
        print(f'ERROR: {exc}',file=sys.stderr);sys.exit(1)
