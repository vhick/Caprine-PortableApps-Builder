"""Dependency-free source-kit structure and workflow contract sanity tests.
These do not claim that Windows app/runtime tests ran locally.
"""
import pathlib, re, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class TestKit(unittest.TestCase):
    def test_files(self):
        for name in ['.github/workflows/build-portable.yml','.github/workflows/repackage-only.yml',
                     'scripts/build.ps1','scripts/patch-upstream.ps1','scripts/resolve.ps1',
                     'scripts/release-selection.ps1','scripts/test-release-selection.ps1',
                     'scripts/release-existence.ps1','scripts/test-release-existence.ps1',
                     'scripts/prepare-repackage.ps1','scripts/verify-integrations.ps1',
                     'scripts/validate-stage.ps1','scripts/verify-installer.ps1',
                     'scripts/package-zip.py','scripts/make-icons.py',
                     'launcher/Program.cs','launcher/CaprinePortable.csproj','README.md','LICENSE']:
            self.assertTrue((ROOT/name).is_file(),name)
    def test_shared_pins(self):
        for filename in ['build-portable.yml','repackage-only.yml']:
            txt=(ROOT/'.github/workflows'/filename).read_text(encoding='utf-8')
            self.assertIn('vhick/Portable-Package-Builder@v1.0.0',txt)
            self.assertIn('vhick/portable-release-publisher@v1.1.1',txt)
            self.assertNotIn('actions/upload-artifact',txt)
            self.assertNotIn('uses: softprops/',txt)
            self.assertIn("prune: 'false'",txt)
            self.assertIn("dry-run: 'true'",txt)
            self.assertIn("dry-run: 'false'",txt)
            self.assertIn('source-dir:',txt)
    def test_launcher_real_source(self):
        code=(ROOT/'launcher/Program.cs').read_text(encoding='utf-8')
        for phrase in ['Process.Start(start)','CAPRINE_PORTABLE_DATA','--traceguard-selftest',
                       'FileAttributes.ReparsePoint','Recovered','Conflicts','session.json',
                       'Directory.CreateDirectory','TraceGuardJsonContext']:
            self.assertIn(phrase,code)
    def test_upstream_patch_anchored(self):
        code=(ROOT/'scripts/patch-upstream.ps1').read_text(encoding='utf-8')
        self.assertIn('app.setPath(\'sessionData\'',code)
        self.assertIn('app.setPath(\'userData\'',code)
        self.assertIn('autoUpdater', (ROOT/'docs/AUDIT.md').read_text(encoding='utf-8'))
        self.assertIn('if(-not $content.Contains($old))',code)
    def test_explicit_utf8_reads(self):
        source=(ROOT/'tests/test_kit_static.py').read_text(encoding='utf-8')
        self.assertNotRegex(source, r'\.read_text\(\)')
        self.assertIn("(ROOT/'docs/AUDIT.md').read_text(encoding='utf-8')", source)

    def test_repack_builder_revision_not_hardcoded(self):
        workflow=(ROOT/'.github/workflows/repackage-only.yml').read_text(encoding='utf-8')
        helper=(ROOT/'scripts/prepare-repackage.ps1').read_text(encoding='utf-8')
        self.assertIn('${{ steps.prep.outputs.builder_revision }}', workflow)
        self.assertIn('builder_revision=$builderRevision', helper)

    def test_resolver_no_direct_rest_array_wrapping(self):
        resolver=(ROOT/'scripts/resolve.ps1').read_text(encoding='utf-8')
        selector=(ROOT/'scripts/release-selection.ps1').read_text(encoding='utf-8')
        runner=(ROOT/'.github/workflows/build-portable.yml').read_text(encoding='utf-8')
        self.assertIn('$rawReleases=Invoke-RestMethod', resolver)
        self.assertIn('Select-CaprineStableRelease -ApiResponse $rawReleases', resolver)
        self.assertIn('Write-Output', selector)
        self.assertIn('test-release-selection.ps1', runner)
        self.assertIn('v2.62.1', (ROOT/'scripts/test-release-selection.ps1').read_text(encoding='utf-8'))
        self.assertIn("BuilderRevision='r4'", resolver)

    def test_existing_release_check_does_not_leak_cli_exit_code(self):
        resolver=(ROOT/'scripts/resolve.ps1').read_text(encoding='utf-8')
        lookup=(ROOT/'scripts/release-existence.ps1').read_text(encoding='utf-8')
        workflow=(ROOT/'.github/workflows/build-portable.yml').read_text(encoding='utf-8')
        regression=(ROOT/'scripts/test-release-existence.ps1').read_text(encoding='utf-8')
        self.assertNotRegex(resolver, r'(?m)^\s*(?:\$\w+\s*=\s*)?&\s*gh\s+release\s+view\b')
        self.assertIn('-SkipHttpErrorCheck -StatusCodeVariable statusCode', resolver)
        self.assertIn('Test-CaprinePublishedRelease', resolver)
        for code in ('404','200'):
            self.assertIn(code,lookup)
        for code in ('401','403','429','500'):
            self.assertIn(code,regression)
        self.assertIn('test-release-existence.ps1',workflow)
        self.assertIn('release-existence.ps1',resolver)

    def test_python_syntax(self):
        for file in (ROOT/'scripts').glob('*.py'):
            compile(file.read_bytes(), str(file),'exec')
if __name__=='__main__':unittest.main()
