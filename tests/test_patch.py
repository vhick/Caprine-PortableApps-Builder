"""Offline fail-closed source adapter fixtures; no Windows runtime assertions."""
import sys,tempfile,unittest,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from patch_caprine import patch

class SourceAdapterTest(unittest.TestCase):
    def prepare(self,tmp):
        d=Path(tmp);(d/'source').mkdir()
        pkg={'version':'2.62.1','main':'dist-js','productName':'Caprine','devDependencies':{'electron':'43.8.6'},
             'build':{'appId':'com.sindresorhus.caprine','win':{'target':'nsis'}}}
        (d/'package.json').write_text(json.dumps(pkg),encoding='utf-8')
        (d/'source/index.ts').write_text("app.setAppUserModelId('com.sindresorhus.caprine');\nif (!is.development && config.get('autoUpdate')) {\n}\n",encoding='utf-8')
        (d/'source/menu.ts').write_text("label: 'Launch at Login',\n\t\t\tvisible: !is.linux,\nlabel: 'Automatic Updates',\n\t\t\ttype: 'checkbox',",encoding='utf-8')
        return d
    def test_guardrails_and_first_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=self.prepare(tmp);patch(d)
            self.assertIn("app.setPath('userData'",(d/'portable-bootstrap.cjs').read_text())
            self.assertIn('setToastActivatorCLSID',(d/'source/index.ts').read_text())
            self.assertIn('!process.env.CAPRINE_PORTABLE_DATA',(d/'source/menu.ts').read_text())
            with self.assertRaises(RuntimeError):patch(d)  # never double-patch
    def test_changed_upstream_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=self.prepare(tmp)
            (d/'source/index.ts').write_text('// changed upstream\n',encoding='utf-8')
            with self.assertRaises(RuntimeError):patch(d)
if __name__=='__main__':unittest.main()
