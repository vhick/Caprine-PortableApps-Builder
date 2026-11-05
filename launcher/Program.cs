using System.Diagnostics;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Runtime.InteropServices;

namespace CaprinePortableLauncher;

public sealed class Scope
{
    public string Name { get; set; } = "";
    public string Host { get; set; } = "";
    // Owned means missing at session entry or created by a previous managed session.
    public bool Owned { get; set; }
}

public sealed class Journal
{
    public bool Active { get; set; }
    public List<Scope> Scopes { get; set; } = [];
}

[JsonSourceGenerationOptions(WriteIndented = true)]
[JsonSerializable(typeof(Journal))]
internal partial class TraceGuardJsonContext : JsonSerializerContext { }

public sealed class TraceGuard
{
    private readonly string data;
    private readonly string trace;
    private readonly string manifest;
    private readonly List<Scope> scopes;
    private Journal journal = new();

    public TraceGuard(string dataRoot, List<Scope> monitored)
    {
        data = dataRoot;
        trace = Path.Combine(data, "TraceGuard");
        manifest = Path.Combine(trace, "session.json");
        scopes = monitored;
        Directory.CreateDirectory(trace);
    }

    private void Log(string message)
    {
        try { File.AppendAllText(Path.Combine(trace, "traceguard.log"),
            $"{DateTimeOffset.UtcNow:O} {message}{Environment.NewLine}"); }
        catch { /* Do not erase or replace logging destination. */ }
    }

    private string Saved(Scope s) => Path.Combine(trace, "Recovered", s.Name, "Caprine");
    private string Conflict(string scope, string relative) => Path.Combine(trace,
        "Conflicts", DateTime.UtcNow.ToString("yyyyMMdd-HHmmss-fffffff") + "-" + Guid.NewGuid().ToString("N"), scope, relative);

    private void StoreJournal()
    {
        var temp = manifest + ".tmp";
        File.WriteAllText(temp, JsonSerializer.Serialize(journal, TraceGuardJsonContext.Default.Journal));
        File.Move(temp, manifest, true);
    }

    private static bool SameFile(string a, string b)
    {
        using var sa = File.OpenRead(a);
        using var sb = File.OpenRead(b);
        return sa.Length == sb.Length && SHA256.HashData(sa).SequenceEqual(SHA256.HashData(sb));
    }

    // Copies every directory, including empty directories. Never follows junctions or symlinks.
    // Conflicting content is preserved, never silently discarded.
    private void CopyTree(string source, string target, string scope, bool overwriteNewer)
    {
        var root = new DirectoryInfo(source);
        if (!root.Exists) return;
        if ((root.Attributes & FileAttributes.ReparsePoint) != 0)
            throw new IOException("Refusing reparse-point root: " + source);
        Directory.CreateDirectory(target);
        // Walk one directory at a time; never recurse through a reparse point.
        var pending = new Stack<DirectoryInfo>();
        pending.Push(root);
        var files = new List<FileInfo>();
        while (pending.Count > 0)
        {
            var current = pending.Pop();
            foreach (var entry in current.EnumerateFileSystemInfos())
            {
                if ((entry.Attributes & FileAttributes.ReparsePoint) != 0)
                    throw new IOException("Refusing reparse-point entry: " + entry.FullName);
                if (entry is DirectoryInfo dir)
                {
                    Directory.CreateDirectory(Path.Combine(target, Path.GetRelativePath(source, dir.FullName)));
                    pending.Push(dir);
                }
                else if (entry is FileInfo file) files.Add(file);
            }
        }
        foreach (var f in files)
        {
            if ((f.Attributes & FileAttributes.ReparsePoint) != 0)
                throw new IOException("Refusing reparse-point file: " + f.FullName);
            string rel = Path.GetRelativePath(source, f.FullName);
            string dest = Path.Combine(target, rel);
            Directory.CreateDirectory(Path.GetDirectoryName(dest)!);
            if (File.Exists(dest) && SameFile(f.FullName, dest)) continue;
            if (File.Exists(dest))
            {
                var existing = new FileInfo(dest);
                bool replace = overwriteNewer && f.LastWriteTimeUtc > existing.LastWriteTimeUtc;
                string preserved = Conflict(scope, rel);
                Directory.CreateDirectory(Path.GetDirectoryName(preserved)!);
                File.Copy(replace ? dest : f.FullName, preserved, false);
                if (!SameFile(replace ? dest : f.FullName, preserved))
                    throw new IOException("Conflict backup verification failed: " + rel);
                Log($"Conflicting file preserved: {preserved}; replace={replace}");
                if (!replace) continue;
            }
            string temporary = dest + ".tg-" + Guid.NewGuid().ToString("N") + ".tmp";
            try
            {
                File.Copy(f.FullName, temporary, false);
                if (!SameFile(f.FullName, temporary)) throw new IOException("Verification failed: " + rel);
                File.Move(temporary, dest, overwriteNewer);
            }
            finally { if (File.Exists(temporary)) File.Delete(temporary); }
        }
    }

    private bool Capture(Scope s)
    {
        if (!s.Owned || !Directory.Exists(s.Host)) return true;
        try
        {
            CopyTree(s.Host, Saved(s), s.Name, true);
            // Remove only a fully verified tree from a scope absent before launch.
            // CopyTree exceptions leave the entire source intact for recovery.
            Directory.Delete(s.Host, true);
            Log("Recovered app-owned scope " + s.Name);
            return true;
        }
        catch (Exception e)
        {
            Log("Recovery left host data intact at " + s.Host + ": " + e);
            return false;
        }
    }

    public void Begin()
    {
        if (File.Exists(manifest))
        {
            try
            {
                var old = JsonSerializer.Deserialize(File.ReadAllText(manifest), TraceGuardJsonContext.Default.Journal);
                if (old?.Active == true)
                {
                    // Crash recovery. Only the locations we owned in the saved journal.
                    // A host path mismatch signals migration / tampering: do not touch it.
                    foreach (var previous in old.Scopes.Where(x => x.Owned))
                    {
                        var current = scopes.FirstOrDefault(x => x.Name == previous.Name &&
                            string.Equals(x.Host, previous.Host, StringComparison.OrdinalIgnoreCase));
                        if (current is null)
                            throw new IOException("Pending recovery refers to a different host scope: " + previous.Host);
                        if (!Capture(previous))
                            throw new IOException("Pending recovery could not safely complete: " + previous.Host);
                    }
                }
            }
            catch (IOException) { throw; }
            catch (Exception e)
            {
                // Fail closed: an unreadable journal may describe a host-owned directory.
                throw new IOException("TraceGuard journal unreadable; refusing to touch external data.", e);
            }
        }
        journal = new Journal { Active = true };
        foreach (var s in scopes)
        {
            bool hostPresent = Directory.Exists(s.Host) || File.Exists(s.Host);
            bool restore = !hostPresent && Directory.Exists(Saved(s));
            var state = new Scope { Name = s.Name, Host = s.Host, Owned = !hostPresent };
            journal.Scopes.Add(state);
            if (restore)
            {
                // Restore only to a nonexistent application-specific host path.
                CopyTree(Saved(s), s.Host, s.Name, false);
                Log("Restored owned prior scope " + s.Name);
            }
            else if (hostPresent)
            {
                Log("Protected pre-existing host path " + s.Host);
            }
        }
        StoreJournal();
    }

    public void End()
    {
        bool all = true;
        foreach (var s in journal.Scopes)
            if (!Capture(s)) all = false;
        if (all) { journal.Active = false; StoreJournal(); }
        else Log("Unfinished recovery retained for next run; see session.json and traceguard.log");
    }

    public static void SelfTest()
    {
        string root = Path.Combine(Path.GetTempPath(), "caprine-traceguard-test-" + Guid.NewGuid().ToString("N"));
        string portable = Path.Combine(root, "Portable", "Data");
        string roam = Path.Combine(root, "Host", "Roaming", "Caprine");
        string local = Path.Combine(root, "Host", "Local", "Caprine");
        List<Scope> locations = [new() { Name = "Roaming", Host = roam }, new() { Name = "Local", Host = local }];
        try
        {
            var guard = new TraceGuard(portable, locations);
            guard.Begin();
            Directory.CreateDirectory(Path.Combine(roam, "nest", "files"));
            File.WriteAllText(Path.Combine(roam, "nest", "files", "content.txt"), "persistent");
            Directory.CreateDirectory(Path.Combine(roam, "empty"));
            Directory.CreateDirectory(Path.Combine(roam, "empty-tree", "child", "grandchild"));
            guard.End();
            string recovered = Path.Combine(portable, "TraceGuard", "Recovered", "Roaming", "Caprine");
            Assert(File.Exists(Path.Combine(recovered, "nest", "files", "content.txt")), "File capture failed");
            Assert(Directory.Exists(Path.Combine(recovered, "empty")), "Empty directory capture failed");
            Assert(Directory.Exists(Path.Combine(recovered, "empty-tree", "child", "grandchild")), "Nested empty tree capture failed");
            Assert(!Directory.Exists(roam), "Owned host cleanup failed");
            guard = new TraceGuard(portable, locations);
            guard.Begin();
            Assert(File.Exists(Path.Combine(roam, "nest", "files", "content.txt")), "Restoration failed");
            var changedFile = Path.Combine(roam, "nest", "files", "content.txt");
            File.WriteAllText(changedFile, "updated and preserved");
            File.SetLastWriteTimeUtc(changedFile, DateTime.UtcNow.AddSeconds(10));
            guard.End();
            Assert(File.ReadAllText(Path.Combine(recovered, "nest", "files", "content.txt")) == "updated and preserved", "Changed file not saved");
            Assert(Directory.EnumerateFiles(Path.Combine(portable, "TraceGuard", "Conflicts"), "content.txt", SearchOption.AllDirectories).Any(), "Old version not safely backed up");
            Directory.CreateDirectory(local);
            File.WriteAllText(Path.Combine(local, "host-profile.txt"), "HOST MUST SURVIVE");
            guard = new TraceGuard(portable, locations);
            guard.Begin();
            Directory.CreateDirectory(Path.Combine(local, "new-empty-dir"));
            guard.End();
            Assert(File.Exists(Path.Combine(local, "host-profile.txt")), "Pre-existing host profile altered");
            Assert(Directory.Exists(Path.Combine(local, "new-empty-dir")), "Pre-existing host directory must be untouched");
            Directory.Delete(local, true);
            guard = new TraceGuard(portable, locations);
            guard.Begin();
            Directory.CreateDirectory(Path.Combine(local, "crash", "empty"));
            // Simulate a launcher crash by starting a new guard without End().
            guard = new TraceGuard(portable, locations);
            guard.Begin();
            Assert(Directory.Exists(Path.Combine(portable, "TraceGuard", "Recovered", "Local", "Caprine", "crash", "empty")), "Crash recovery failed");
            guard.End();
            File.WriteAllText(Path.Combine(portable, "TraceGuard", "selftest-passed.txt"), "PASS");
        }
        finally { try { Directory.Delete(root, true); } catch { } }
    }

    private static void Assert(bool condition, string error)
    {
        if (!condition) throw new InvalidOperationException(error);
    }
}

internal static class Program
{
    [DllImport("user32.dll", CharSet = CharSet.Unicode, EntryPoint = "MessageBoxW")]
    private static extern int MessageBox(nint owner, string message, string title, uint type);

    private static void Alert(string detail)
    {
        try { MessageBox(0, detail, "Caprine Portable", 0x10); } catch { }
    }

    private static bool IsAppRunning(string executable)
    {
        foreach (var p in Process.GetProcessesByName("Caprine"))
        {
            try
            {
                if (!p.HasExited && string.Equals(p.MainModule?.FileName, executable,
                    StringComparison.OrdinalIgnoreCase)) return true;
            }
            catch { /* Restricted unrelated processes are not ours. */ }
            finally { p.Dispose(); }
        }
        return false;
    }

    private static string MutexName(string root)
    {
        byte[] digest = SHA256.HashData(System.Text.Encoding.UTF8.GetBytes(Path.GetFullPath(root).ToUpperInvariant()));
        return "Local\\CaprinePortable-" + Convert.ToHexString(digest.AsSpan(0, 12));
    }

    [STAThread]
    private static int Main(string[] args)
    {
        try
        {
            if (args.Length == 1 && args[0] == "--shellguard-selftest")
            {
                ShellTraceGuard.SelfTest();
                return 0;
            }
            if (args.Length == 1 && args[0] == "--traceguard-selftest")
            {
                TraceGuard.SelfTest();
                return 0;
            }
            string root = AppContext.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
            string exe = Path.Combine(root, "App", "Caprine", "Caprine.exe");
            if (!File.Exists(exe)) throw new FileNotFoundException("Packaged Caprine.exe was not found", exe);
            string data = Path.Combine(root, "Data");
            Directory.CreateDirectory(data);
            string profile = Path.Combine(data, "Profile");
            Directory.CreateDirectory(profile);
            using var mutex = new Mutex(false, MutexName(root));
            bool acquired;
            try { acquired = mutex.WaitOne(0); }
            catch (AbandonedMutexException) { acquired = true; }
            if (!acquired) throw new InvalidOperationException("This portable package is already running.");
            try
            {
                if (IsAppRunning(exe))
                    throw new InvalidOperationException("Caprine is still running. Exit Caprine from its tray icon before reopening the portable launcher.");
                List<Scope> paths = [
                    new() { Name = "Roaming", Host = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "Caprine") },
                    new() { Name = "Local", Host = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Caprine") }
                ];
                var guard = new TraceGuard(data, paths);
                guard.Begin();
                var shellGuard = new ShellTraceGuard(data, exe);
                bool shellStarted = false;
                try
                {
                    shellGuard.Begin();
                    shellStarted = true;
                    var start = new ProcessStartInfo(exe)
                    {
                        UseShellExecute = false,
                        WorkingDirectory = Path.GetDirectoryName(exe)!
                    };
                    start.Environment["CAPRINE_PORTABLE_DATA"] = profile;
                    foreach (string argument in args) start.ArgumentList.Add(argument);
                    using var process = Process.Start(start) ?? throw new InvalidOperationException("Unable to start Caprine.");
                    // Closing the GUI can hide Caprine to tray. Wait for actual process exit.
                    // A grace window handles Electron's app.relaunch() behavior.
                    process.WaitForExit();
                    DateTime? quietSince = null;
                    while (true)
                    {
                        if (IsAppRunning(exe)) quietSince = null;
                        else quietSince ??= DateTime.UtcNow;
                        if (quietSince is not null && (DateTime.UtcNow - quietSince.Value).TotalSeconds >= 4) break;
                        Thread.Sleep(350);
                    }
                    return 0;
                }
                finally
                {
                    // Must run after the Electron process and its notification worker exit.
                    // If interrupted, each active journal is replayed on the next launch.
                    try { if (shellStarted) shellGuard.End(); }
                    finally { guard.End(); }
                }
            }
            finally { mutex.ReleaseMutex(); }
        }
        catch (Exception e)
        {
            try
            {
                string data = Path.Combine(AppContext.BaseDirectory, "Data", "TraceGuard");
                Directory.CreateDirectory(data);
                File.AppendAllText(Path.Combine(data, "launcher-errors.log"), $"{DateTimeOffset.UtcNow:O} {e}{Environment.NewLine}");
            }
            catch { }
            // CI test mode must never show a modal GUI on an unattended runner.
            if (!(args.Length == 1 && (args[0] == "--traceguard-selftest" || args[0] == "--shellguard-selftest")))
                Alert(e.Message + "\n\nSee Data\\TraceGuard\\launcher-errors.log for details.");
            return 1;
        }
    }
}
