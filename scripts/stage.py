#!/usr/bin/env python3
"""Stage x64 Caprine PortableApps independently of the shared installer action."""
import argparse,configparser,hashlib,json,re,shutil,sys
from pathlib import Path
from PIL import Image


def make_stage(args):
    source=Path(args.source).resolve(); appsrc=Path(args.app).resolve()
    launchersrc=Path(args.launcher).resolve(); stage=Path(args.stage).resolve()
    identity=json.loads(Path(args.identity).read_text(encoding='utf-8'))
    version=identity['version']
    if not re.fullmatch(r'\d+\.\d+\.\d+',version): raise RuntimeError('Bad semantic version')
    if not re.fullmatch(r'r[1-9][0-9]*',args.revision): raise RuntimeError('Bad builder revision')
    package_version=f'{version}.{int(args.revision[1:])}' 
    if stage.exists(): raise RuntimeError('Staging path must be clean; refusing to overwrite')
    expected_exe=appsrc/'Caprine.exe'
    for needed in (expected_exe,appsrc/'resources'/'app.asar',launchersrc,source/'build'/'icon.png',source/'license'):
        if not needed.is_file(): raise RuntimeError(f'Missing required source component: {needed}')
    stage.mkdir(parents=True)
    shutil.copytree(appsrc,stage/'App'/'Caprine')
    shutil.copy2(launchersrc,stage/'CaprinePortable.exe')
    appinfo=stage/'App'/'AppInfo';appinfo.mkdir()
    image=Image.open(source/'build'/'icon.png').convert('RGBA')
    image.resize((16,16),Image.Resampling.LANCZOS).save(appinfo/'appicon_16.png')
    image.resize((32,32),Image.Resampling.LANCZOS).save(appinfo/'appicon_32.png')
    image.save(appinfo/'appicon.ico',format='ICO',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    ini=f'''[Format]
Type=PortableApps.comFormat
Version=3.7

[Details]
Name=Caprine Portable (Unofficial Community Build)
AppID=CaprinePortable-vhick
Publisher=Sindre Sorhus and bankjaneo; portable integration by community
Homepage=https://github.com/bankjaneo/caprine
Category=Internet
Description=Caprine Facebook Messenger desktop client with separate portable profile
Language=English

[License]
Shareable=true
OpenSource=true
Freeware=true
CommercialUse=true

[Version]
PackageVersion={package_version}
DisplayVersion={version} r{args.revision.lstrip('r')}

[Control]
Icons=1
Start=CaprinePortable.exe
'''
    (appinfo/'appinfo.ini').write_text(ini,encoding='utf-8')
    (stage/'Data'/'Profile').mkdir(parents=True)
    (stage/'Data'/'Session').mkdir(parents=True)
    (stage/'Data'/'Logs').mkdir(parents=True)
    (stage/'Data'/'CrashDumps').mkdir(parents=True)
    (stage/'Data'/'TraceGuard'/'Recovered'/'StartMenu').mkdir(parents=True)
    (stage/'Data'/'TraceGuard'/'Recovered'/'Registry').mkdir(parents=True)
    (stage/'Other'/'Source').mkdir(parents=True)
    shutil.copy2(source/'license',stage/'Other'/'Source'/'UPSTREAM_LICENSE.txt')
    (stage/'Other'/'Source'/'PORTABLE_CHANGES.txt').write_text(
        f'Original repository: https://github.com/bankjaneo/caprine\nTag: {identity["tag"]}\n'
        f'Source commit: {identity["commit"]}\npackage-lock SHA-256: {identity["lock_sha256"]}\n'
        'Portable modifications: main bootstrap, distinct userData/sessionData/logs/crashDumps, '
        'distinct AUMID and toast CLSID, disable upstream auto-updater and login registration, C# root launcher + narrow ShellGuard.\n',encoding='utf-8')
    (stage/'Other'/'Source'/'BUILD_IDENTITY.json').write_text(json.dumps({**identity,'builder_revision':args.revision,'mode':'PORTABLEAPPS','architecture':'x64'},indent=2)+'\n',encoding='utf-8')
    (stage/'Other'/'Source'/'README.txt').write_text(
        'Source-built unofficial portable edition. Original upstream license in UPSTREAM_LICENSE.txt.\n'
        'User data goes under Data; optional notification shell recovery goes under Data\\TraceGuard.\n'
        'Do not delete Data when upgrading or uninstalling. Application updates are handled by this builder, NOT Caprine.\n',encoding='utf-8')
    (stage/'README.txt').write_text(
        'Caprine Portable (unofficial)\n\nRun CaprinePortable.exe. Keep the entire directory together.\n'
        'For upgrades, close Caprine, back up Data, then replace App and CaprinePortable.exe while leaving Data untouched.\n'
        'Close using the Caprine menu Quit/Exit rather than only X (tray may remain active).\n'
        'Check Data\\TraceGuard\\shellguard.log after notification tests.\n'
        'Messenger login/credentials may use Windows-protected encryption; moving to another Windows account may require logging in again.\n'
        'Downloads explicitly saved by the user use their Windows Downloads folder and are NOT migrated.\n',encoding='utf-8')
    print('STAGED',stage)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for arg in ('source','app','launcher','stage','identity','revision'):p.add_argument('--'+arg,required=True)
    options=p.parse_args()
    try: make_stage(options)
    except Exception as exc:print('ERROR: '+str(exc),file=sys.stderr);sys.exit(1)
