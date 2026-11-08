#!/usr/bin/env python3
"""PortableApps staging/zip validation; does NOT claim interactive Windows portability."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED,is_zipfile
import argparse, configparser,hashlib,json,struct,sys, re, os

def pe(path:Path, target:int=0x8664):
    size=path.stat().st_size
    with path.open('rb') as f:
        header=f.read(64)
        if header[:2]!=b'MZ' or len(header)<64: raise AssertionError(f'Invalid PE MZ: {path}')
        offset=struct.unpack_from('<I',header,0x3c)[0]
        if offset<64 or offset+24>size: raise AssertionError(f'Invalid PE offset: {path}')
        f.seek(offset); sig=f.read(6)
        if sig[:4]!=b'PE\0\0': raise AssertionError(f'Invalid PE signature: {path}')
        arch=struct.unpack_from('<H',sig,4)[0]
        if arch!=target: raise AssertionError(f'Unexpected architecture {hex(arch)}: {path}')

def stage(root:Path,version:str,revision:str='r1'):
    for rel in ('CaprinePortable.exe','App/Caprine/Caprine.exe','App/Caprine/resources/app.asar',
      'App/AppInfo/appinfo.ini','App/AppInfo/appicon.ico','App/AppInfo/appicon_16.png',
      'App/AppInfo/appicon_32.png','Data/Profile','Data/Session','Data/TraceGuard/Recovered/StartMenu',
      'Other/Source/UPSTREAM_LICENSE.txt','Other/Source/BUILD_IDENTITY.json'):
        assert (root/rel).exists(),f'Missing {rel}'
    pe(root/'CaprinePortable.exe');pe(root/'App/Caprine/Caprine.exe')
    parser=configparser.ConfigParser(interpolation=None);parser.read(root/'App/AppInfo/appinfo.ini',encoding='utf-8')
    assert parser['Format']['Type']=='PortableApps.comFormat'
    assert parser['Details']['AppID']=='CaprinePortable-vhick'
    assert parser['Control']['Start']=='CaprinePortable.exe'
    assert re.fullmatch(r'r[1-9][0-9]*',revision), 'Bad builder revision'
    assert parser['Version']['PackageVersion']==version+'.'+str(int(revision[1:]))
    identity=json.loads((root/'Other/Source/BUILD_IDENTITY.json').read_text(encoding='utf-8'))
    assert identity['version']==version and len(identity['commit'])==40 and len(identity['lock_sha256'])==64
    assert not (root/'App'/'Caprine'/'Data').exists(), 'wrong-mode data layout'
    assert not list(root.rglob('*.cmd')), 'no CMD-only launchers in runtime package'
    print('STATIC-VALIDATED: PE x64, layout, icons, metadata, identity, Data directories')

def zip_stage(root:Path,dest:Path):
    if dest.exists():raise AssertionError(f'Won\'t overwrite ZIP {dest}')
    dest.parent.mkdir(parents=True,exist_ok=True)
    # Include directory entries: empty directories and recovery hierarchy survive extraction.
    with ZipFile(dest,'w',ZIP_DEFLATED,compresslevel=6,allowZip64=True) as z:
        prefix=root.name+'/'
        z.writestr(prefix,b'')
        for item in sorted(root.rglob('*')):
            arc=prefix+item.relative_to(root).as_posix()
            if item.is_symlink():raise AssertionError(f'Symlink not allowed in package: {item}')
            if item.is_dir():z.writestr(arc+'/',b'')
            elif item.is_file():z.write(item,arc)
    assert is_zipfile(dest)
    with ZipFile(dest) as z:
        failures=z.testzip()
        assert failures is None,f'ZIP CRC failure {failures}'
        names=set(z.namelist())
        assert root.name+'/Data/TraceGuard/Recovered/StartMenu/' in names
        assert root.name+'/CaprinePortable.exe' in names
        assert root.name+'/App/Caprine/Caprine.exe' in names
        assert all(p.startswith(root.name+'/') for p in names)
    print('STATIC-VALIDATED: ZIP CRC, retained empty directories, expected portable root')
    print('ZIP_SHA256',hashlib.sha256(dest.read_bytes()).hexdigest(),dest.name)

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',required=True);p.add_argument('--version',required=True);p.add_argument('--revision',default='r1');p.add_argument('--zip')
    args=p.parse_args();root=Path(args.stage).resolve();stage(root,args.version,args.revision)
    if args.zip:zip_stage(root,Path(args.zip).resolve())
if __name__=='__main__':
    try:main()
    except Exception as exc:print(f'ERROR: {exc}',file=sys.stderr);sys.exit(1)
