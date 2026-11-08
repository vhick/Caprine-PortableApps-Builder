#!/usr/bin/env python3
"""Skip already published, publisher-owned exact-build releases; fail on ownership conflicts."""
import argparse,os,json,urllib.request,urllib.error,sys

def inspect(repo,tag):
    headers={'Accept':'application/vnd.github+json','User-Agent':'CaprinePortableBuilder-r1'}
    if os.environ.get('GH_TOKEN'):headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
    req=urllib.request.Request(f'https://api.github.com/repos/{repo}/releases/tags/{tag}',headers=headers)
    try:
        with urllib.request.urlopen(req,timeout=30) as response:record=json.load(response)
    except urllib.error.HTTPError as e:
        if e.code==404:return False
        raise RuntimeError(f'Release status check HTTP {e.code}') from e
    if record.get('draft') or '<!-- portable-release-publisher:managed:v2 -->' not in record.get('body',''):
        raise RuntimeError('Tag already exists but is draft/non-publisher-owned; refusing to overwrite')
    names={x.get('name','') for x in record.get('assets',[])}
    if not any(x.endswith('.zip') for x in names) or 'SHA256SUMS.txt' not in names:
        raise RuntimeError('Publisher-managed release has incomplete assets; manual review required')
    return True
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--tag',required=True);p.add_argument('--repo',required=True);args=p.parse_args()
    try:
        skip=inspect(args.repo,args.tag)
        print('Existing identical publisher release' if skip else 'No existing release for exact build')
        if os.environ.get('GITHUB_OUTPUT'):
            with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as out:out.write(f'skip={str(skip).lower()}\n')
    except Exception as exc:print('ERROR: '+str(exc),file=sys.stderr);sys.exit(1)
