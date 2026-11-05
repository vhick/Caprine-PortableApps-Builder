using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;
using Microsoft.Win32;

namespace CaprinePortableLauncher;

// Electron 43's Windows toast activator creates a per-user Start Menu shortcut and
// HKCU\Software\Classes\CLSID entries at runtime. This guard only touches identities
// created by our portable run; it never sweeps shared Windows shell folders/registry.
public sealed class ShellTraceJournal
{
    public bool Active { get; set; }
    public string ShortcutPath { get; set; } = "";
    public string ExecutablePath { get; set; } = "";
    public bool ShortcutAbsentAtStart { get; set; }
    public List<string> ExistingClsidKeys { get; set; } = [];
}

[JsonSourceGenerationOptions(WriteIndented = true)]
[JsonSerializable(typeof(ShellTraceJournal))]
internal partial class ShellTraceJsonContext : JsonSerializerContext { }

public sealed class ShellTraceGuard
{
    public const string ShortcutFile = "Caprine Portable.lnk";
    private readonly string trace;
    private readonly string journalPath;
    private readonly string programs;
    private readonly string executable;
    private readonly string registryRoot;
    private ShellTraceJournal journal = new();

    public ShellTraceGuard(string dataRoot, string executablePath, string? programsDirectory = null,
        string registryRoot = @"Software\Classes\CLSID")
    {
        trace = Path.Combine(dataRoot, "TraceGuard");
        Directory.CreateDirectory(trace);
        journalPath = Path.Combine(trace, "shell-session.json");
        programs = programsDirectory ?? Environment.GetFolderPath(Environment.SpecialFolder.Programs);
        executable = Path.GetFullPath(executablePath);
        this.registryRoot = registryRoot;
    }

    private void Log(string message)
    {
        File.AppendAllText(Path.Combine(trace, "shell-guard.log"),
            $"{DateTimeOffset.UtcNow:O} {message}{Environment.NewLine}");
    }

    private void Save()
    {
        string temporary = journalPath + ".tmp";
        File.WriteAllText(temporary, JsonSerializer.Serialize(journal, ShellTraceJsonContext.Default.ShellTraceJournal));
        File.Move(temporary, journalPath, true);
    }

    private static bool SameFile(string first, string second)
    {
        using var a = File.OpenRead(first);
        using var b = File.OpenRead(second);
        return a.Length == b.Length && SHA256.HashData(a).SequenceEqual(SHA256.HashData(b));
    }

    private static bool NoReparsePoint(string path)
    {
        if (!File.Exists(path)) return true;
        return (File.GetAttributes(path) & FileAttributes.ReparsePoint) == 0;
    }

    private HashSet<string> MatchingRegistryKeys(string target)
    {
        HashSet<string> matched = new(StringComparer.OrdinalIgnoreCase);
        using var clsid = Registry.CurrentUser.OpenSubKey(registryRoot, false);
        if (clsid is null) return matched;
        foreach (var id in clsid.GetSubKeyNames())
        {
            if (!id.StartsWith('{') || !id.EndsWith('}')) continue;
            using var node = clsid.OpenSubKey(id, false);
            using var localServer = node?.OpenSubKey("LocalServer32", false);
            if (node is null || localServer is null) continue;
            if (!string.Equals(node.GetValue(null) as string, "Electron Notification Activator", StringComparison.Ordinal)) continue;
            if (Convert.ToInt32(node.GetValue("CustomActivator") ?? 0) != 1) continue;
            string? writtenTarget = localServer.GetValue(null) as string;
            if (!string.IsNullOrEmpty(writtenTarget) &&
                string.Equals(Path.GetFullPath(writtenTarget.Trim('"')), target, StringComparison.OrdinalIgnoreCase))
                matched.Add(id);
        }
        return matched;
    }

    private void CleanRegistry(ShellTraceJournal state)
    {
        var protectedKeys = new HashSet<string>(state.ExistingClsidKeys, StringComparer.OrdinalIgnoreCase);
        foreach (string key in MatchingRegistryKeys(state.ExecutablePath))
        {
            if (protectedKeys.Contains(key)) continue;
            using (var node = Registry.CurrentUser.OpenSubKey(registryRoot + @"\" + key, false))
            {
                // Never delete a node another application extended beyond Electron's known structure.
                if (node is null || node.GetSubKeyNames().Any(n => !n.Equals("LocalServer32", StringComparison.OrdinalIgnoreCase)))
                {
                    Log("Protected unfamiliar registry layout: " + key);
                    continue;
                }
                if (node.GetValueNames().Any(n => n != "" && n != "CustomActivator"))
                {
                    Log("Protected unexpected registry value: " + key);
                    continue;
                }
            }
            // Repeat the exact target match immediately before deleting.
            if (!MatchingRegistryKeys(state.ExecutablePath).Contains(key)) continue;
            Registry.CurrentUser.DeleteSubKeyTree(registryRoot + @"\" + key, false);
            Log("Removed portable-owned Electron toast activator CLSID " + key);
        }
    }

    private void CaptureShortcut(ShellTraceJournal state)
    {
        if (!state.ShortcutAbsentAtStart || !File.Exists(state.ShortcutPath)) return;
        if (!NoReparsePoint(state.ShortcutPath))
        {
            Log("Refused shortcut reparse point: " + state.ShortcutPath);
            throw new IOException("Unexpected shortcut reparse point. Host file untouched.");
        }
        // Only the exact portable-specific name, absent at start, is eligible.
        // The portable-only productName and AppUserModelId isolate it from installed Caprine.
        string archive = Path.Combine(trace, "Recovered", "StartMenu");
        Directory.CreateDirectory(archive);
        string target = Path.Combine(archive,
            DateTime.UtcNow.ToString("yyyyMMdd-HHmmss-fffffff") + "-" + Guid.NewGuid().ToString("N") + ".lnk");
        File.Copy(state.ShortcutPath, target, false);
        if (!SameFile(state.ShortcutPath, target))
            throw new IOException("Start Menu shortcut backup verification failed.");
        // Fail closed if another process replaced it between the copy and deletion.
        if (!SameFile(state.ShortcutPath, target))
            throw new IOException("Start Menu shortcut changed after backup; source retained.");
        File.Delete(state.ShortcutPath);
        Log("Recovered runtime-created shortcut to " + target);
    }

    private void Recover(ShellTraceJournal state)
    {
        if (!state.Active) return;
        // Manifest is absolute because it identifies exactly which host location this run changed.
        // Refuse to touch arbitrary paths if an untrusted journal was modified or host user changed.
        if (!string.Equals(state.ShortcutPath, Path.Combine(programs, ShortcutFile), StringComparison.OrdinalIgnoreCase))
            throw new IOException("Previous shell journal shortcut path differs from this Windows account; manual recovery required.");
        CaptureShortcut(state);
        CleanRegistry(state);
        Log("Recovered interrupted shell integration session.");
    }

    public void Begin()
    {
        if (File.Exists(journalPath))
        {
            var old = JsonSerializer.Deserialize(File.ReadAllText(journalPath), ShellTraceJsonContext.Default.ShellTraceJournal)
                ?? throw new IOException("Unreadable shell integration manifest.");
            Recover(old);
        }
        string candidate = Path.Combine(programs, ShortcutFile);
        if (File.Exists(candidate))
        {
            // Electron overwrites a same-name shortcut automatically. Do not risk a host-owned link.
            throw new IOException("A Start Menu shortcut already exists at " + candidate +
                ". It may belong to another installation. Move or rename it manually only after checking its target.");
        }
        journal = new ShellTraceJournal
        {
            Active = true,
            ExecutablePath = executable,
            ShortcutPath = candidate,
            ShortcutAbsentAtStart = true,
            ExistingClsidKeys = MatchingRegistryKeys(executable).OrderBy(x => x, StringComparer.OrdinalIgnoreCase).ToList()
        };
        Save();
    }

    public void End()
    {
        // If cleanup fails, leave Active=true to retry on the next launch.
        CaptureShortcut(journal);
        CleanRegistry(journal);
        journal.Active = false;
        Save();
    }

    public static void SelfTest()
    {
        string root = Path.Combine(Path.GetTempPath(), "caprine-shellguard-test-" + Guid.NewGuid().ToString("N"));
        string programs = Path.Combine(root, "Programs");
        string data = Path.Combine(root, "Data");
        string executable = Path.Combine(root, "App", "Caprine", "Caprine.exe");
        string regBase = @"Software\CaprinePortableShellSelfTest\" + Guid.NewGuid().ToString("N") + @"\CLSID";
        Directory.CreateDirectory(programs);
        Directory.CreateDirectory(Path.GetDirectoryName(executable)!);
        File.WriteAllText(executable, "test-only-not-an-executable");
        try
        {
            using (var baseKey = Registry.CurrentUser.CreateSubKey(regBase)) { }
            var guard = new ShellTraceGuard(data, executable, programs, regBase);
            guard.Begin();
            File.WriteAllText(Path.Combine(programs, ShortcutFile), "test link");
            var id = Guid.NewGuid().ToString("B");
            using (var key = Registry.CurrentUser.CreateSubKey(regBase + @"\" + id))
            {
                key!.SetValue(null, "Electron Notification Activator");
                key.SetValue("CustomActivator", 1, RegistryValueKind.DWord);
                using var child = key.CreateSubKey("LocalServer32");
                child!.SetValue(null, executable);
            }
            guard.End();
            if (File.Exists(Path.Combine(programs, ShortcutFile))) throw new Exception("Runtime shortcut was not recovered.");
            using (var deleted = Registry.CurrentUser.OpenSubKey(regBase + @"\" + id))
                if (deleted is not null) throw new Exception("Runtime registry entry was not cleaned.");
            if (!Directory.EnumerateFiles(Path.Combine(data, "TraceGuard", "Recovered", "StartMenu"), "*.lnk").Any())
                throw new Exception("No recovered shortcut stored in Data.");
            // Preexisting shortcut: application must refuse to run and must not alter it.
            File.WriteAllText(Path.Combine(programs, ShortcutFile), "pre-existing host shortcut");
            bool blocked = false;
            try { new ShellTraceGuard(data, executable, programs, regBase).Begin(); }
            catch (IOException) { blocked = true; }
            if (!blocked || File.ReadAllText(Path.Combine(programs, ShortcutFile)) != "pre-existing host shortcut")
                throw new Exception("Pre-existing Start Menu entry was not protected.");
            File.Delete(Path.Combine(programs, ShortcutFile));
            // Pre-existing registry entries pointing to the same executable must survive.
            var hostKey = Guid.NewGuid().ToString("B");
            using (var key = Registry.CurrentUser.CreateSubKey(regBase + @"\" + hostKey))
            {
                key!.SetValue(null, "Electron Notification Activator");
                key.SetValue("CustomActivator", 1, RegistryValueKind.DWord);
                using var local = key.CreateSubKey("LocalServer32");
                local!.SetValue(null, executable);
            }
            guard = new ShellTraceGuard(data, executable, programs, regBase);
            guard.Begin();
            guard.End();
            using (var protectedEntry = Registry.CurrentUser.OpenSubKey(regBase + @"\" + hostKey))
                if (protectedEntry is null) throw new Exception("Pre-existing registry entry was altered.");
            // Simulate crash: launcher never called End(), so next Begin must clean before reopening.
            guard = new ShellTraceGuard(data, executable, programs, regBase);
            guard.Begin();
            File.WriteAllText(Path.Combine(programs, ShortcutFile), "interrupted run");
            guard = new ShellTraceGuard(data, executable, programs, regBase);
            guard.Begin();
            if (File.Exists(Path.Combine(programs, ShortcutFile))) throw new Exception("Crash recovery shortcut failed.");
            guard.End();
            using (var protectedEntry = Registry.CurrentUser.OpenSubKey(regBase + @"\" + hostKey))
                if (protectedEntry is null) throw new Exception("Pre-existing CLSID did not survive crash recovery.");
        }
        finally
        {
            Registry.CurrentUser.DeleteSubKeyTree(@"Software\CaprinePortableShellSelfTest\" + regBase.Split('\\')[2], false);
            try { Directory.Delete(root, true); } catch { }
        }
    }
}
