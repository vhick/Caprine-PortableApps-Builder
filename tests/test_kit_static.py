"""Dependency-free source-kit structure and workflow contract sanity tests.
These do not claim that Windows app/runtime tests ran locally.
"""
import pathlib, re, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class TestKit(unittest.TestCase):
    def test_files(self):
        for name in ['.github/workflows/build-portable.yml','.github/workflows/repackage-only.yml',
                     'scripts/build.ps1','scripts/patch-upstream.ps1','scripts/resolve.ps1',
                     'scripts/prepare-repackage.ps1','scripts/verify-integrations.ps1',
                     'scripts/validate-stage.ps1','scripts/verify-installer.ps1',
                     'scripts/package-zip.py','scripts/make-icons.py',
                     'launcher/Program.cs','launcher/CaprinePortable.csproj','README.md','LICENSE']:
            self.assertTrue((ROOT/name).is_file(),name)
    def test_shared_pins(self):
        for filename in ['build-portable.yml','repackage-only.yml']:
            txt=(ROOT/'.github/workflows'/filename).read_text()
            self.assertIn('vhick/Portable-Package-Builder@v1.0.0',txt)
            self.assertIn('vhick/portable-release-publisher@v1.1.1',txt)
            self.assertNotIn('actions/upload-artifact',txt)
            self.assertNotIn('uses: softprops/',txt)
            self.assertIn("prune: 'false'",txt)
            self.assertIn("dry-run: 'true'",txt)
            self.assertIn("dry-run: 'false'",txt)
            self.assertIn('source-dir:',txt)
    def test_launcher_real_source(self):
        code=(ROOT/'launcher/Program.cs').read_text()
        for phrase in ['Process.Start(start)','CAPRINE_PORTABLE_DATA','--traceguard-selftest',
                       'FileAttributes.ReparsePoint','Recovered','Conflicts','session.json',
                       'Directory.CreateDirectory','TraceGuardJsonContext']:
            self.assertIn(phrase,code)
    def test_upstream_patch_anchored(self):
        code=(ROOT/'scripts/patch-upstream.ps1').read_text()
        self.assertIn('app.setPath(\'sessionData\'',code)
        self.assertIn('app.setPath(\'userData\'',code)
        self.assertIn('autoUpdater', (ROOT/'docs/AUDIT.md').read_text())
        self.assertIn('if(-not $content.Contains($old))',code)
    def test_python_syntax(self):
        for file in (ROOT/'scripts').glob('*.py'):
            compile(file.read_bytes(), str(file),'exec')
if __name__=='__main__':unittest.main()
