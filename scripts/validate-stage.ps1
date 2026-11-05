param([Parameter(Mandatory)][string]$Stage)
$ErrorActionPreference='Stop'
function CheckPE([string]$File){
 $f=[IO.File]::OpenRead($File)
 try {
  if($f.Length -lt 128){throw "Too small PE: $File"}
  $r=[IO.BinaryReader]::new($f)
  if($r.ReadUInt16() -ne 0x5A4D){throw "Missing MZ: $File"}
  $f.Position=0x3C;$offset=$r.ReadInt32()
  if($offset -lt 64 -or $offset -ge ($f.Length - 4)){throw "Invalid PE offset: $File"}
  $f.Position=$offset
  if($r.ReadUInt32() -ne 0x4550){throw "Missing PE signature: $File"}
 } finally {$f.Dispose()}
}
CheckPE (Join-Path $Stage 'CaprinePortable.exe')
CheckPE (Join-Path $Stage 'App/Caprine/Caprine.exe')
foreach($p in @('App/AppInfo/appinfo.ini','App/AppInfo/appicon.ico','App/AppInfo/appicon_16.png','App/AppInfo/appicon_32.png','Other/Source/UPSTREAM.txt')){
 if(-not (Test-Path (Join-Path $Stage $p))){throw "Missing $p"}
}
foreach($p in @('App','Other')){
 $items=@(Get-Item (Join-Path $Stage $p)) + @(Get-ChildItem (Join-Path $Stage $p) -Recurse -Force)
 foreach($i in $items){if(($i.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0){throw "Reparse point in package $($i.FullName)"}}
}
# Automated true native EXE execution, without launching Facebook UI in CI.
$testProcess=Start-Process -FilePath (Join-Path $Stage 'CaprinePortable.exe') -ArgumentList '--traceguard-selftest' -PassThru -Wait
if($testProcess.ExitCode -ne 0){throw "Native launcher / empty-folder / crash-recovery test failed (exit $($testProcess.ExitCode))"}
Write-Host 'PASS: native launcher executed; TraceGuard file, empty-dir, nested-empty-dir, host-protection, repeat and crash fixtures.'

# Electron 43 toast activator creates AppUserModelId shortcuts/CLSID entries on Windows.
# Execute the C# shell regression in a temporary namespace, never touching real app entries.
$shellTest=Start-Process -FilePath (Join-Path $Stage 'CaprinePortable.exe') -ArgumentList '--shellguard-selftest' -PassThru -Wait
if($shellTest.ExitCode -ne 0){throw "Native shell integration / shortcut / registry / crash fixture failed (exit $($shellTest.ExitCode))"}
Write-Host 'PASS: portable shell integration (shortcut capture, CLSID cleanup, host protection, crash recovery).'
