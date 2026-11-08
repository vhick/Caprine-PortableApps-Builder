#!/usr/bin/env python3
"""Pinned-source-compatible, fail-closed Caprine PORTABLEAPPS adaptation."""
import argparse, json, re, sys
from pathlib import Path
GUID = '{E79A08F5-09E3-4F25-988A-7C0BB6096C60}'
AUMID = 'com.vhick.caprine.portable'
BOOTSTRAP = r'''// Caprine Portable bootstrap: runs BEFORE require('./dist-js/index.js') and electron-store.
'use strict';
const path = require('node:path');
const fs = require('node:fs');
const {app} = require('electron');
const root = process.env.CAPRINE_PORTABLE_DATA;
if (!root || !path.isAbsolute(root)) {
  throw new Error('Caprine Portable must be launched via CaprinePortable.exe');
}
// Distinct portable profile. Do not alter Windows-wide APPDATA, LOCALAPPDATA or TEMP.
const profile = path.join(root, 'Profile');
const session = path.join(root, 'Session');
const logs = path.join(root, 'Logs');
const crashes = path.join(root, 'CrashDumps');
for (const dir of [root, profile, session, logs, crashes]) {
  fs.mkdirSync(dir, {recursive: true});
}
app.setPath('userData', profile);
app.setPath('sessionData', session);
app.setPath('crashDumps', crashes);
app.setAppLogsPath(logs);
require('./dist-js/index.js');
'''

def exact_replace(text, old, new, place):
    if text.count(old)!=1: raise RuntimeError(f'Upstream changed {place}: expected one exact match, got {text.count(old)}')
    return text.replace(old,new)

def patch(root: Path):
    pkg_path=root/'package.json';pkg=json.loads(pkg_path.read_text(encoding='utf-8'))
    if not re.fullmatch(r'2\.\d+\.\d+',pkg.get('version','')):raise RuntimeError('Unexpected upstream package version')
    if 'electron' not in pkg.get('devDependencies',{}):raise RuntimeError('Electron dependency absent')
    if pkg.get('main')!='dist-js':raise RuntimeError('Unexpected upstream main; bootstrap requires re-audit')
    pkg['main']='portable-bootstrap.cjs'
    pkg['productName']='Caprine Portable'
    pkg['build']['appId']=AUMID
    pkg['build']['win']['executableName']='Caprine'
    # Installer is generated separately by the shared Package Builder, not electron-builder.
    # Windows --dir below selects unpacked output; do not register the upstream NSIS target.
    (root/'portable-bootstrap.cjs').write_text(BOOTSTRAP,encoding='utf-8')
    pkg_path.write_text(json.dumps(pkg,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    index=root/'source/index.ts'
    src=index.read_text(encoding='utf-8')
    src=exact_replace(src,"app.setAppUserModelId('com.sindresorhus.caprine');",
        "app.setAppUserModelId('com.vhick.caprine.portable');\n"
        "if (process.platform === 'win32') {\n"
        f"\tapp.setToastActivatorCLSID('{GUID}');\n"
        "}", 'source/index.ts AppUserModelId')
    src=exact_replace(src,"if (!is.development && config.get('autoUpdate')) {",
        "if (!is.development && !process.env.CAPRINE_PORTABLE_DATA && config.get('autoUpdate')) {",
        'source/index.ts automatic updater')
    index.write_text(src,encoding='utf-8')
    menu=root/'source/menu.ts'
    src=menu.read_text(encoding='utf-8')
    # Disallow registration from the app's menu; an optional OS autostart manager is NOT included.
    src=exact_replace(src,"label: 'Launch at Login',\n\t\t\tvisible: !is.linux,",
        "label: 'Launch at Login',\n\t\t\tvisible: !is.linux && !process.env.CAPRINE_PORTABLE_DATA,",
        'source/menu.ts login option')
    src=exact_replace(src,"label: 'Automatic Updates',\n\t\t\ttype: 'checkbox',",
        "label: 'Automatic Updates',\n\t\t\tvisible: !process.env.CAPRINE_PORTABLE_DATA,\n\t\t\ttype: 'checkbox',",
        'source/menu.ts update option')
    menu.write_text(src,encoding='utf-8')
    assert BOOTSTRAP.find("app.setPath('userData'")<BOOTSTRAP.rfind("require('./dist-js/index.js')")
    print('Caprine portable source adapter applied (separate data, AUMID/CLSID, opt-in shell, updater disabled).')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('source');args=parser.parse_args()
    try:patch(Path(args.source).resolve())
    except Exception as exc:print(f'ERROR: {exc}',file=sys.stderr);sys.exit(1)
