"""Create and independently verify a ready-to-extract PortableApps ZIP."""
from pathlib import Path
import argparse, configparser, hashlib, json, struct, zipfile
p=argparse.ArgumentParser()
p.add_argument('--stage', required=True)
p.add_argument('--out',required=True)
p.add_argument('--revision',default='r2')
a=p.parse_args()
root=Path(a.stage).resolve(); out=Path(a.out); out.mkdir(parents=True,exist_ok=True)
assert root.name=='CaprinePortable',f'Unexpected portable root {root.name}'
ini=configparser.ConfigParser(interpolation=None)
ini.optionxform=str
ini.read(root/'App/AppInfo/appinfo.ini')
assert ini['Details']['AppID']=='CaprinePortable'
assert ini['Control']['Start']=='CaprinePortable.exe'
assert ini['Format']['Type']=='PortableApps.comFormat'
ver=ini['Version']['DisplayVersion']
assert len(ver.split('.'))==3 and all(part.isdigit() for part in ver.split('.'))
required=['CaprinePortable.exe','App/Caprine/Caprine.exe','App/AppInfo/appicon.ico','App/AppInfo/appicon_16.png','App/AppInfo/appicon_32.png','App/AppInfo/appinfo.ini','Other/Source/UPSTREAM.txt']
for rel in required:
    if not (root/rel).is_file():raise SystemExit('Missing required staged file: '+rel)
def pe(f):
    with f.open('rb') as h:
        b=h.read(64)
        if len(b)!=64 or b[:2]!=b'MZ':return False
        o=struct.unpack_from('<I',b,60)[0]
        h.seek(o)
        return h.read(4)==b'PE\0\0'
for rel in ['CaprinePortable.exe','App/Caprine/Caprine.exe']:
    if not pe(root/rel):raise SystemExit('Not an actual Windows PE: '+rel)
if any((root/'Data').rglob('*')):raise SystemExit('Data must be empty in a distributed package')
filename=f'CaprinePortable_{ver}_{a.revision}.zip';path=out/filename
if path.exists():raise SystemExit(f'Refusing to overwrite package: {path}')
with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7,allowZip64=True) as z:
    z.writestr('CaprinePortable/','')
    for x in sorted(root.rglob('*')):
        if x.is_symlink():raise SystemExit(f'Symlink in staging input: {x}')
        rel=x.relative_to(root).as_posix();arc='CaprinePortable/'+rel
        if x.is_dir():z.writestr(arc+'/','')
        elif x.is_file():z.write(x,arc)
with zipfile.ZipFile(path) as z:
    corrupt=z.testzip()
    if corrupt:raise SystemExit(f'Corrupt zip member: {corrupt}')
    for rel in required:
        if 'CaprinePortable/'+rel not in z.namelist():raise SystemExit(f'ZIP missing: {rel}')
    for d in ['CaprinePortable/Data/','CaprinePortable/App/DefaultData/']:
        if d not in z.namelist():raise SystemExit(f'ZIP missing empty directory: {d}')
    if any('..' in Path(x).parts or x.startswith('/') for x in z.namelist()):
        raise SystemExit('Unsafe ZIP member path')
sha=hashlib.sha256(path.read_bytes()).hexdigest()
print(json.dumps(dict(file=str(path),sha256=sha,upstream_version=ver),indent=2))
