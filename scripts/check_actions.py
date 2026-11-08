#!/usr/bin/env python3
"""CI verification of exact pinned shared action tags and documented interfaces."""
import json,subprocess,sys,urllib.request
SOURCES=[
 ('vhick/Portable-Package-Builder','v1.0.0','0112c35','inputs:',
  ('source-dir','output-dir','engine','running-exe','timeout-seconds','package-revision','official-tool-url','official-tool-sha256'),
  ('installer-file','installer-sha256','app-id','app-version')),
 ('vhick/portable-release-publisher','v1.1.1','cb64f86','inputs:',
  ('files','tag','release-title','tag-prefix','keep-releases','prune','dry-run'),())]

def run():
    for repo,tag,expected_prefix,marker,ins,outs in SOURCES:
        remote='https://github.com/'+repo+'.git'
        cp=subprocess.run(['git','ls-remote','--tags',remote,'refs/tags/'+tag],capture_output=True,text=True,check=True,timeout=60)
        if not cp.stdout.strip():raise RuntimeError('Missing action tag: '+repo+'@'+tag)
        # Lightweight tag or annotated peeled tag: ensure the verified release commit remains pinned.
        lines=[x.split('\t',1) for x in cp.stdout.splitlines() if '\t' in x]
        advertised=lines[0][0]
        if not advertised.startswith(expected_prefix):
            # Annotated tags require a peeled commit.
            peeled=subprocess.run(['git','ls-remote','--tags',remote,'refs/tags/'+tag+'^{}'],capture_output=True,text=True,check=True,timeout=60).stdout.strip()
            if not peeled or not peeled.split('\t')[0].startswith(expected_prefix):
                raise RuntimeError(f'Pinned action tag moved: {repo}@{tag}; refusing unreviewed code')
        url=f'https://raw.githubusercontent.com/{repo}/{tag}/action.yml'
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'CaprinePortableBuilder-r1'}),timeout=30) as r:body=r.read().decode('utf-8')
        if marker not in body or 'using: composite' not in body:raise RuntimeError('Action is not expected composite: '+repo)
        before,_,tail=body.partition('outputs:')
        for key in ins:
            if f'  {key}:' not in before:raise RuntimeError(f'Missing {repo}@{tag} input: {key}')
        for key in outs:
            if f'  {key}:' not in tail:raise RuntimeError(f'Missing {repo}@{tag} output: {key}')
        print('Verified pinned shared action source/interface:',repo+'@'+tag)
if __name__=='__main__':
    try:run()
    except Exception as exc:print('ERROR: '+str(exc),file=sys.stderr);sys.exit(1)
