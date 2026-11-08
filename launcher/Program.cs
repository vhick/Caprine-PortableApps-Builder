using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;
using Microsoft.Win32;

namespace CaprinePortable;

internal static class Program
{
    // This is a genuine compiled Windows launcher, never a renamed script.
    [STAThread]
    private static int Main(string[] args)
    {
        var root = Path.GetFullPath(AppContext.BaseDirectory);
        var exe = Path.Combine(root, "App", "Caprine", "Caprine.exe");
        var data = Path.Combine(root, "Data");
        Directory.CreateDirectory(data);
        var guard = new ShellGuard(data, exe);
        using var mutex = new Mutex(true, "Local\\CaprinePortableVhick-" + Convert.ToHexString(SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(root.ToLowerInvariant())))[..16], out bool first);
        if (!first) return 0; // Do not launch a second manager against the same Data.
        try
        {
            if (!File.Exists(exe)) throw new FileNotFoundException("Packaged Caprine.exe missing", exe);
            guard.RecoverPreviousSessionIfSafe();
            guard.Begin();
            var info = new ProcessStartInfo(exe)
            {
                UseShellExecute = false,
                WorkingDirectory = Path.GetDirectoryName(exe)!,
            };
            info.Environment["CAPRINE_PORTABLE_DATA"] = data;
            foreach (var argument in args) info.ArgumentList.Add(argument);
            using var child = Process.Start(info) ?? throw new InvalidOperationException("Failed to start Caprine");
            // A Windows job tracks Chromium renderers and application relaunch descendants.
            using var job = JobTracker.TryCreate();
            if (job != null && job.Attach(child))
                job.WaitUntilNoProcesses();
            else
            {
                guard.Log("Job association unavailable; waiting for the root process only. Child-exit validation required.");
                child.WaitForExit();
                // Never collect shell entries if child ownership/lifecycle is uncertain.
                guard.MarkUnsafeExit();
            }
            guard.End();
            return 0;
        }
        catch (Exception ex)
        {
            guard.Log("Launcher error: " + ex);
            System.Windows.Forms.MessageBox.Show(ex.Message, "Caprine Portable", System.Windows.Forms.MessageBoxButtons.OK, System.Windows.Forms.MessageBoxIcon.Error);
            return 1;
        }
    }
}

internal sealed class JobTracker : IDisposable
{
    private IntPtr handle;
    private JobTracker(IntPtr h) => handle = h;
    public static JobTracker? TryCreate()
    {
        var handle = CreateJobObject(IntPtr.Zero, null);
        return handle == IntPtr.Zero ? null : new JobTracker(handle);
    }
    public bool Attach(Process child)
    {
        // Windows runners/portable environments may already impose a job.
        return AssignProcessToJobObject(handle, child.Handle);
    }
    public void WaitUntilNoProcesses()
    {
        // Job objects do NOT signal on normal process exit. Query active process count.
        while (true)
        {
            if (!QueryInformationJobObject(handle, 1, out var info, (uint)Marshal.SizeOf<BasicAccounting>(), IntPtr.Zero))
                throw new InvalidOperationException("Unable to verify complete Electron child process shutdown");
            if (info.ActiveProcesses == 0) return;
            Thread.Sleep(300);
        }
    }
    public void Dispose() { if (handle!=IntPtr.Zero) {CloseHandle(handle); handle=IntPtr.Zero;} }
    [StructLayout(LayoutKind.Sequential)]
    internal struct BasicAccounting
    {
        public long TotalUserTime, TotalKernelTime, ThisPeriodTotalUserTime, ThisPeriodTotalKernelTime;
        public uint TotalPageFaultCount, TotalProcesses, ActiveProcesses, TotalTerminatedProcesses;
    }
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    private static extern IntPtr CreateJobObject(IntPtr security, string? name);
    [DllImport("kernel32.dll", SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
    [DllImport("kernel32.dll", SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool QueryInformationJobObject(IntPtr job, int infoClass, out BasicAccounting info, uint length, IntPtr returned);
    [DllImport("kernel32.dll", SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CloseHandle(IntPtr handle);
}

internal sealed class ShellGuard
{
    private const string Clsid = "{E79A08F5-09E3-4F25-988A-7C0BB6096C60}";
    private const string ClsidPath = @"Software\Classes\CLSID\" + Clsid;
    private readonly string data, exe, startMenu, manifest, logFile;
    private Manifest? snapshot;
    private bool unsafeExit;
    private record Manifest(string Exe, Dictionary<string,string> Shortcuts, bool ClsidExisted, DateTime StartedUtc);
    public ShellGuard(string dataRoot, string caprineExe)
    {
        data=dataRoot; exe=Path.GetFullPath(caprineExe);
        startMenu=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),@"Microsoft\Windows\Start Menu\Programs");
        manifest=Path.Combine(data,"TraceGuard","pending-shellguard.json");
        logFile=Path.Combine(data,"TraceGuard","shellguard.log");
        Directory.CreateDirectory(Path.GetDirectoryName(manifest)!);
    }
    public void Log(string message) => File.AppendAllText(logFile, $"{DateTime.UtcNow:O} {message}{Environment.NewLine}");
    public void MarkUnsafeExit() => unsafeExit=true;
    private static bool ExpectedName(string path)
    {
        var name=Path.GetFileName(path);
        return name.Equals("Caprine Portable.lnk",StringComparison.OrdinalIgnoreCase)
            || name.Equals("CaprinePortable.lnk",StringComparison.OrdinalIgnoreCase)
            || name.Equals("Caprine.lnk",StringComparison.OrdinalIgnoreCase);
    }
    private Dictionary<string,string> Shortcuts()
    {
        var entries=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase);
        if (!Directory.Exists(startMenu)) return entries;
        // BOUNDED: immediate top-level expected Caprine shortcut names only.
        foreach (string entry in Directory.EnumerateFiles(startMenu,"*.lnk",SearchOption.TopDirectoryOnly))
        {
            if (!ExpectedName(entry)) continue;
            try { entries[entry] = Hash(entry); }
            catch (Exception ex) { Log("Skipped inaccessible shortcut: "+ex.Message); }
        }
        return entries;
    }
    private static string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path)));
    private bool PortableCaprineProcessStillRunning()
    {
        foreach (var p in Process.GetProcessesByName("Caprine"))
        {
            using (p)
            {
                try
                {
                    if (!p.HasExited && p.MainModule?.FileName?.Equals(exe, StringComparison.OrdinalIgnoreCase)==true)
                        return true;
                }
                catch (System.ComponentModel.Win32Exception)
                {
                    // A process that cannot be inspected makes cleanup unsafe.
                    return true;
                }
                catch (InvalidOperationException) { }
            }
        }
        return false;
    }
    public void Begin()
    {
        if (File.Exists(manifest)) throw new IOException("Unresolved previous shell operation; close Caprine and examine Data\\TraceGuard\\pending-shellguard.json");
        using var priorClsid = Registry.CurrentUser.OpenSubKey(ClsidPath);
        snapshot=new Manifest(exe, Shortcuts(), priorClsid!=null,DateTime.UtcNow);
        AtomicWrite(snapshot);
    }
    public void RecoverPreviousSessionIfSafe()
    {
        if (!File.Exists(manifest)) return;
        try
        {
            var old=JsonSerializer.Deserialize<Manifest>(File.ReadAllText(manifest));
            if (old==null || !Path.GetFullPath(old.Exe).Equals(exe,StringComparison.OrdinalIgnoreCase))
            {
                Log("Previous manifest references a different location; preserving it for manual review.");
                return;
            }
            // On restart a previous crash may have left Caprine running. Never clean during activity.
            if (PortableCaprineProcessStillRunning())
            {
                Log("Caprine process exists; deferring previous cleanup."); return;
            }
            Reconcile(old);
        }
        catch (Exception ex) {Log("Previous recovery postponed: " + ex);}
    }
    public void End()
    {
        if (snapshot==null || unsafeExit) { Log("Post-exit cleanup skipped: process ownership not proven.");return; }
        Reconcile(snapshot);
    }
    private void Reconcile(Manifest state)
    {
        bool unresolved = false;
        foreach (var pair in Shortcuts())
        {
            // Existing user/installed shortcuts must never be moved or deleted.
            if (state.Shortcuts.ContainsKey(pair.Key)) continue;
            if (!ShortcutPointsToExactExecutable(pair.Key, exe))
            {
                Log("Unverified new shortcut preserved: "+pair.Key); unresolved = true; continue;
            }
            try
            {
                var dest=Path.Combine(data,"TraceGuard","Recovered","StartMenu",Path.GetFileName(pair.Key));
                Directory.CreateDirectory(Path.GetDirectoryName(dest)!);
                if (File.Exists(dest)) {Log("Recovery destination exists; preserving host shortcut: "+pair.Key);unresolved=true;continue;}
                var sourceHash=Hash(pair.Key);
                File.Copy(pair.Key,dest,false);
                if (Hash(dest)!=sourceHash || Hash(pair.Key)!=sourceHash) throw new IOException("Shortcut copy/fingerprint changed");
                // Only remove after a fully verified recovery copy. If it changes concurrently, preserve it.
                if (Hash(pair.Key)!=sourceHash) throw new IOException("Shortcut changed before removal");
                File.Delete(pair.Key);
                Log("Recovered new portable shortcut: "+dest);
            }
            catch (Exception ex) {unresolved=true; Log("Shortcut retained (cannot safely recover): "+ex);}
        }
        if (!state.ClsidExisted && !RecoverOwnedClsid()) unresolved = true;
        if (unresolved)
        {
            // Retain complete evidence in Data and leave ambiguous host state untouched.
            string dir=Path.Combine(data,"TraceGuard","Unresolved");
            Directory.CreateDirectory(dir);
            string archive=Path.Combine(dir,"session-"+DateTime.UtcNow.ToString("yyyyMMddHHmmssfff")+".json");
            File.Copy(manifest,archive,false);
            Log("Incomplete recovery preserved for review: "+archive);
        }
        try {File.Delete(manifest);}catch (Exception ex){Log("Cannot clear old manifest: "+ex.Message);}
    }
    private static bool ShortcutPointsToExactExecutable(string shortcut, string expected)
    {
        // Windows Script Host COM: resolves binary .lnk target. No link text/path guesses.
        try
        {
            var type=Type.GetTypeFromProgID("WScript.Shell");
            if (type==null) return false;
            var shell=Activator.CreateInstance(type)!;
            try
            {
                dynamic link=((dynamic)shell).CreateShortcut(shortcut);
                string target=(string)link.TargetPath;
                string arguments=(string)link.Arguments;
                return string.IsNullOrWhiteSpace(arguments)
                    && Path.GetFullPath(target).Equals(expected,StringComparison.OrdinalIgnoreCase);
            }
            finally { if (Marshal.IsComObject(shell)) Marshal.FinalReleaseComObject(shell); }
        }
        catch {return false;}
    }
    private bool RecoverOwnedClsid()
    {
        using var key=Registry.CurrentUser.OpenSubKey(ClsidPath);
        if (key==null) return true;
        // Only a single unshared LocalServer32 subkey is safe to recover automatically.
        if (key.GetValueNames().Any(n => n.Length != 0) ||
            key.GetSubKeyNames().Any(n => !n.Equals("LocalServer32", StringComparison.OrdinalIgnoreCase)))
        { Log("Unexpected CLSID subkey; preserving registry state"); return false; }
        using var server=key.OpenSubKey("LocalServer32");
        if (server != null && (server.GetSubKeyNames().Length != 0 || server.GetValueNames().Any(n => n.Length != 0)))
        { Log("Unexpected CLSID server values; preserving registry state"); return false; }
        var command=server?.GetValue(null) as string;
        if (string.IsNullOrWhiteSpace(command) || !command.Contains(exe,StringComparison.OrdinalIgnoreCase))
        {
            Log("Portable CLSID exists but executable ownership cannot be proven; preserving HKCU\\"+ClsidPath);
            return false;
        }
        var target=Path.Combine(data,"TraceGuard","Recovered","Registry","portable-toast-"+DateTime.UtcNow.ToString("yyyyMMddHHmmssfff")+".reg");
        Directory.CreateDirectory(Path.GetDirectoryName(target)!);
        try
        {
            using var p=Process.Start(new ProcessStartInfo("reg.exe")
            {
                UseShellExecute=false, CreateNoWindow=true,
                ArgumentList={"export",@"HKCU\"+ClsidPath,target,"/y"}
            }) ?? throw new IOException("reg.exe did not start");
            p.WaitForExit(15000);
            if (!p.HasExited || p.ExitCode!=0 || !File.Exists(target) || new FileInfo(target).Length<30)
                throw new IOException("Registry export failed");
            using (var recheck=Registry.CurrentUser.OpenSubKey(ClsidPath))
            using (var serverAgain=recheck?.OpenSubKey("LocalServer32"))
            {
                var newCommand=serverAgain?.GetValue(null) as string;
                if (newCommand != command) throw new IOException("Registry changed during export");
            }
            Registry.CurrentUser.DeleteSubKeyTree(ClsidPath,false);
            Log("Recovered newly created portable CLSID backup: "+target);
            return true;
        }
        catch(Exception ex){Log("CLSID preserved for safety: "+ex); return false;}
    }
    private void AtomicWrite(Manifest state)
    {
        var temp=manifest+".tmp";
        File.WriteAllText(temp,JsonSerializer.Serialize(state,new JsonSerializerOptions{WriteIndented=true}));
        File.Move(temp,manifest,true);
    }
}
