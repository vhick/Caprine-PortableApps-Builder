"""Offline package staging/zip/empty-directory fixtures; NOT real Caprine binaries."""
import json,sys,tempfile,unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from stage import make_stage
from validate import stage,zip_stage
from test_validate import make_pe

class StageTest(unittest.TestCase):
    def test_completely_empty_directory_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); src=root/'upstream';(src/'build').mkdir(parents=True)
            (src/'build'/'icon.png').parent.mkdir(exist_ok=True)
            Image.new('RGB',(256,256),'white').save(src/'build'/'icon.png')
            (src/'license').write_text('MIT test fixture')
            app=root/'unpacked';(app/'resources').mkdir(parents=True)
            (app/'Caprine.exe').write_bytes(make_pe(0x8664))
            (app/'resources'/'app.asar').write_bytes(b'fixture only')
            launcher=root/'CaprinePortable.exe';launcher.write_bytes(make_pe(0x8664))
            ident=root/'identity.json';ident.write_text(json.dumps({'tag':'v2.62.1','version':'2.62.1','commit':'a'*40,'lock_sha256':'b'*64}))
            from argparse import Namespace
            staged=root/'stage'/'CaprinePortable'
            make_stage(Namespace(source=str(src),app=str(app),launcher=str(launcher),stage=str(staged),identity=str(ident),revision='r1'))
            stage(staged,'2.62.1','r1')
            from configparser import ConfigParser
            ini=ConfigParser()
            ini.read(staged/'App'/'AppInfo'/'appinfo.ini',encoding='utf-8')
            self.assertEqual(ini['Version']['PackageVersion'],'2.62.1.1')
            self.assertEqual(ini['Details']['AppID'],'CaprinePortable-vhick')
            with self.assertRaises(AssertionError):stage(staged,'2.62.1','r2')
            target=root/'portable.zip';zip_stage(staged,target)
            from zipfile import ZipFile
            with ZipFile(target) as z:
                self.assertIn('CaprinePortable/Data/TraceGuard/Recovered/StartMenu/',z.namelist())
                self.assertIn('CaprinePortable/Data/TraceGuard/Recovered/Registry/',z.namelist())
if __name__=='__main__':unittest.main()
