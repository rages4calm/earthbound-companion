// SPDX-License-Identifier: GPL-3.0-or-later
using System.Diagnostics;
using System.Formats.Tar;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text.Json;

namespace EarthBoundCompanion;
public static partial class UpdateService {
    static FileStream? handoffGate;
    // Keep coordination files outside a macOS .app so its signed resource
    // envelope remains identical to the freshly built release.
    static string PendingPath(string install) => SafeFile(Path.GetDirectoryName(Path.GetFullPath(install).TrimEnd(Path.DirectorySeparatorChar))!, "."+Path.GetFileName(install)+"-eb-update-result.json");
    public sealed record PackageFile(string Path, string Sha256);
    public sealed record UpdatePlan(string Install, string Platform, string Version, int Parent, List<PackageFile> Files);
    public sealed record UpdateResult(string Work, bool Success, string Message);
    static readonly JsonSerializerOptions JsonOptions = new(){WriteIndented=true};
    static StringComparison PathComparison => OperatingSystem.IsWindows() ? StringComparison.OrdinalIgnoreCase : StringComparison.Ordinal;
    static string WorkPrefix(string install) => "."+Path.GetFileName(install)+"-eb-update-";
    public static bool IsInstalledRelease(string directory) => File.Exists(Path.Combine(directory,LauncherRelative)) && File.Exists(Path.Combine(directory,EngineRelative));
    public static bool IsGameRunning(string directory) {
        string expected=Path.GetFullPath(Path.Combine(directory,EngineRelative));
        foreach(var process in Process.GetProcessesByName(Path.GetFileNameWithoutExtension(expected))) {
            using(process) try { if(string.Equals(process.MainModule?.FileName,expected,PathComparison))return true; }
            catch(Exception e) when(e is System.ComponentModel.Win32Exception or InvalidOperationException or NotSupportedException) {
                // An unreadable matching process might still be using this engine.
                return true;
            }
        }
        return false;
    }
    static bool PrivatePath(string relative) {
        var parts=relative.Replace('\\','/').Split('/');
        return parts.Any(p=>new[]{"UserData","saves","msu","screenshots","ContentProfiles","Seeds"}.Contains(p,StringComparer.OrdinalIgnoreCase))
            || new[]{".pak",".srm",".sav",".state",".pcm"}.Contains(Path.GetExtension(relative),StringComparer.OrdinalIgnoreCase)
            || new[]{"config.ini","earthbound.ini","settings.dat","settings.json","keybinds.ini"}.Contains(parts[^1],StringComparer.OrdinalIgnoreCase);
    }
    static string SafeFile(string root,string relative) {
        relative=relative.Replace('\\','/');
        var parts=relative.Split('/');
        if(parts.Any(p=>p is "" or "." or ".." || p.Contains(':') || p.Contains('\0') || p.EndsWith('.') || p.EndsWith(' ')) || Path.IsPathRooted(relative))
            throw new UpdateException("The update contains an unsafe file path.");
        string anchor=Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar);
        string full=Path.GetFullPath(Path.Combine(anchor,relative));
        if(!full.StartsWith(anchor+Path.DirectorySeparatorChar,PathComparison))throw new UpdateException("The update escaped its staging folder.");
        string? check=full;
        while(check!=null) {
            if((File.Exists(check)||Directory.Exists(check)) && (File.GetAttributes(check)&FileAttributes.ReparsePoint)!=0)
                throw new UpdateException("An update path is a symbolic link. Use a physical installation folder.");
            // System/home ancestors may be redirected (macOS /var -> /private/var).
            // The chosen root and every child are still checked for links.
            if(string.Equals(check,anchor,PathComparison))break;
            check=Path.GetDirectoryName(check);
        }
        return full;
    }
    public static List<PackageFile> ExtractPackage(string archive,string destination,string platform) {
        Directory.CreateDirectory(destination);
        var seen=new HashSet<string>(StringComparer.OrdinalIgnoreCase); long total=0;
        var files=new List<PackageFile>();
        void Write(string name,long length,Stream input,UnixFileMode? mode=null) {
            if(PrivatePath(name))throw new UpdateException("A release unexpectedly contains player data. It was refused.");
            var output=SafeFile(destination,name);
            if(!seen.Add(name))throw new UpdateException("The update lists a file twice.");
            total=checked(total+length);if(total>MaxPackageBytes)throw new UpdateException("The unpacked update is too large.");
            Directory.CreateDirectory(Path.GetDirectoryName(output)!);
            using(var file=new FileStream(output,FileMode.CreateNew))input.CopyTo(file);
            if(!OperatingSystem.IsWindows()&&mode!=null)File.SetUnixFileMode(output,mode.Value & (UnixFileMode)0x1ff);
            using var read=File.OpenRead(output);files.Add(new(name,Convert.ToHexString(SHA256.HashData(read))));
        }
        if(platform=="win-x64") {
            using var zip=ZipFile.OpenRead(archive);
            foreach(var entry in zip.Entries) {
                string name=entry.FullName.Replace('\\','/');
                const string prefix="EarthBound Companion/";
                if(!name.StartsWith(prefix,StringComparison.Ordinal))throw new UpdateException("The Windows update has an unexpected folder layout.");
                name=name[prefix.Length..];if(name==""||name.EndsWith('/'))continue;
                if(((entry.ExternalAttributes>>16)&0xf000)==0xa000)throw new UpdateException("Update archives cannot contain symbolic links.");
                using var data=entry.Open();Write(name,entry.Length,data);
            }
        } else {
            using var raw=File.OpenRead(archive);using var gzip=new GZipStream(raw,CompressionMode.Decompress);using var tar=new TarReader(gzip);
            TarEntry? entry;
            while((entry=tar.GetNextEntry())!=null) {
                string name=entry.Name;while(name.StartsWith("./",StringComparison.Ordinal))name=name[2..];
                if(entry.EntryType==TarEntryType.Directory){if(name.TrimEnd('/')!="")SafeFile(destination,name.TrimEnd('/'));continue;}
                if(platform.StartsWith("osx-")) {
                    const string prefix="EarthBound Companion Preview.app/";
                    if(!name.StartsWith(prefix,StringComparison.Ordinal))throw new UpdateException("The macOS update has an unexpected app bundle.");
                    name=name[prefix.Length..];
                }
                if(entry.EntryType is not (TarEntryType.RegularFile or TarEntryType.V7RegularFile) || entry.DataStream==null)
                    throw new UpdateException("The update contains an unsupported link or special file.");
                Write(name,entry.Length,entry.DataStream,entry.Mode);
            }
        }
        string launcher=platform=="win-x64"?"EarthBound Companion.exe":platform.StartsWith("osx-")?"Contents/MacOS/EarthBoundCompanion.Portable":"EarthBoundCompanion.Portable";
        string engine=platform=="win-x64"?"Game/earthbound.exe":platform.StartsWith("osx-")?"Contents/MacOS/Game/earthbound":"Game/earthbound";
        if(!seen.Contains(launcher)||!seen.Contains(engine))throw new UpdateException("The update is missing its launcher or game executable.");
        return files;
    }
    public static async Task<string> StageAsync(string install,UpdateRelease release,IProgress<UpdateProgress>? progress=null,CancellationToken cancel=default) {
        if(OperatingSystem.IsAndroid())throw new UpdateException("Android installs updates through its package installer.");
        install=Path.GetFullPath(install).TrimEnd(Path.DirectorySeparatorChar);
        if(!IsInstalledRelease(install))throw new UpdateException("Extract and run a complete release before updating.");
        if(IsGameRunning(install))throw new UpdateException("Close the game before updating.");
        string parent=Path.GetDirectoryName(install)??throw new UpdateException("Install the game inside a folder before updating.");
        string work=Path.Combine(parent,WorkPrefix(install)+Guid.NewGuid().ToString("N"));
        PendingPath(install);
        Directory.CreateDirectory(work);
        try {
            string archive=Path.Combine(work,release.Zip.Name);
            await DownloadAsync(release,archive,progress,cancel:cancel).ConfigureAwait(false);
            cancel.ThrowIfCancellationRequested();progress?.Report(new("Unpacking verified update",0,1));
            var files=await Task.Run(()=>ExtractPackage(archive,Path.Combine(work,"new"),Platform),cancel).ConfigureAwait(false);
            foreach(var file in files)SafeFile(install,file.Path);
            var plan=new UpdatePlan(install,Platform,release.Version.ToString(),Environment.ProcessId,files);
            string path=Path.Combine(work,"plan.json");await File.WriteAllTextAsync(path,JsonSerializer.Serialize(plan,JsonOptions),cancel).ConfigureAwait(false);
            File.Delete(archive);
            // Process exit releases this lease even while Unix still lists the
            // parent as a zombie. Waiting for its PID alone can deadlock a
            // launcher started by Steam or another process that captures output.
            handoffGate?.Dispose();
            handoffGate=new FileStream(Path.Combine(work,"launcher.lock"),FileMode.CreateNew,FileAccess.ReadWrite,FileShare.None);
            return path;
        }catch{Directory.Delete(work,true);throw;}
    }
    public static Process StartHelper(string planPath) {
        string work=Path.GetDirectoryName(planPath)!;
        var start=new ProcessStartInfo(Path.Combine(work,"new",LauncherRelative)){WorkingDirectory=work,UseShellExecute=false,CreateNoWindow=true};
        start.ArgumentList.Add("--apply-update");start.ArgumentList.Add(planPath);
        return Process.Start(start)??throw new UpdateException("The update helper did not start. Your current installation is unchanged.");
    }
    public static bool HandleHelper(string[] args) {
        if(args.Length!=2||args[0]!="--apply-update")return false;
        UpdatePlan? attempted=null;bool trustedLocation=false;
        try {
            var plan=JsonSerializer.Deserialize<UpdatePlan>(File.ReadAllText(args[1]))??throw new UpdateException("Missing update plan.");
            string work=Path.GetFullPath(Path.GetDirectoryName(args[1])!);
            string own=Path.GetFullPath(Environment.ProcessPath!);
            if(!own.Equals(Path.Combine(work,"new",LauncherRelative),PathComparison))throw new UpdateException("The update helper must run from its verified staging folder.");
            trustedLocation=Path.GetDirectoryName(work)==Path.GetDirectoryName(Path.GetFullPath(plan.Install).TrimEnd(Path.DirectorySeparatorChar)) && Path.GetFileName(work).StartsWith(WorkPrefix(plan.Install),StringComparison.Ordinal);
            if(!trustedLocation)throw new UpdateException("The staging folder does not belong to this installation.");
            attempted=plan;
            WaitForLauncherExit(work,plan.Parent);
            ApplyPlan(plan,work);
            Process.Start(new ProcessStartInfo(Path.Combine(plan.Install,LauncherRelative)){WorkingDirectory=plan.Install,UseShellExecute=false});
        }catch(Exception error) {
            string log=Path.Combine(Path.GetDirectoryName(args[1])!,"update-error.txt");
            try{File.WriteAllText(log,error.ToString());}catch(IOException){}
            if(trustedLocation&&attempted!=null)try {
                string marker=PendingPath(attempted.Install);
                File.WriteAllText(marker,JsonSerializer.Serialize(new UpdateResult(Path.GetDirectoryName(args[1])!,false,error.Message+" Details: "+log)));
                Process.Start(new ProcessStartInfo(Path.Combine(attempted.Install,LauncherRelative)){WorkingDirectory=attempted.Install,UseShellExecute=false});
            }catch(Exception){ /* Keep the staged backup and error log for recovery. */ }
            Environment.ExitCode=1;
        }
        return true;
    }
    static void WaitForLauncherExit(string work,int parentId) {
        string lease=SafeFile(work,"launcher.lock");
        if(!File.Exists(lease))throw new UpdateException("The update handoff is incomplete. Check for updates again.");
        var deadline=Stopwatch.StartNew();
        while(true) {
            try{using var released=new FileStream(lease,FileMode.Open,FileAccess.ReadWrite,FileShare.None);break;}
            catch(IOException) when(deadline.Elapsed<TimeSpan.FromSeconds(60)){Thread.Sleep(100);}
        }
        if(OperatingSystem.IsWindows())try {
            using var parent=Process.GetProcessById(parentId);
            if(parent.Id==Environment.ProcessId||!parent.WaitForExit(60000))throw new UpdateException("Close the previous launcher and try again.");
        }catch(ArgumentException){}
    }
    // Every destination is backed up before replacement. A failure restores the
    // exact bytes and permissions already installed; player data is never touched.
    public static void ApplyPlan(UpdatePlan plan,string work,Action<string>? step=null) {
        string install=Path.GetFullPath(plan.Install).TrimEnd(Path.DirectorySeparatorChar);
        work=Path.GetFullPath(work).TrimEnd(Path.DirectorySeparatorChar);
        if(plan.Platform!=Platform || Path.GetDirectoryName(work)!=Path.GetDirectoryName(install) || !Path.GetFileName(work).StartsWith(WorkPrefix(install),StringComparison.Ordinal))
            throw new UpdateException("The update staging folder does not belong to this installation.");
        SafeFile(Path.GetDirectoryName(work)!,Path.GetFileName(work)+"/plan.json");
        if(!IsInstalledRelease(install)||IsGameRunning(install))throw new UpdateException("Close the game before applying this update.");
        string staged=Path.Combine(work,"new"),backup=Path.Combine(work,"backup");
        string lockPath=SafeFile(Path.GetDirectoryName(install)!, "."+Path.GetFileName(install)+"-eb-update.lock");
        using var gate=new FileStream(lockPath,FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None);
        var seen=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach(var f in plan.Files) {
            if(PrivatePath(f.Path)||!seen.Add(f.Path))throw new UpdateException("Unsafe update plan.");
            string source=SafeFile(staged,f.Path);SafeFile(install,f.Path);SafeFile(backup,f.Path);
            using var stream=File.OpenRead(source);
            if(!Convert.ToHexString(SHA256.HashData(stream)).Equals(f.Sha256,StringComparison.OrdinalIgnoreCase))throw new UpdateException("The staged update changed after verification.");
        }
        if(!seen.Contains(LauncherRelative)||!seen.Contains(EngineRelative))throw new UpdateException("Incomplete update plan.");
        var replaced=new List<(string Path,bool Existed)>();
        try {
            foreach(var f in plan.Files) {
                string dest=SafeFile(install,f.Path),source=SafeFile(staged,f.Path),saved=SafeFile(backup,f.Path);
                bool existed=File.Exists(dest);
                if(existed){Directory.CreateDirectory(Path.GetDirectoryName(saved)!);File.Copy(dest,saved,false);CopyMode(dest,saved);}
                replaced.Add((f.Path,existed));step?.Invoke(f.Path);
                Directory.CreateDirectory(Path.GetDirectoryName(dest)!);File.Copy(source,dest,true);CopyMode(source,dest);
            }
            File.WriteAllText(PendingPath(install),JsonSerializer.Serialize(new UpdateResult(work,true,"Update installed. Saves, settings and game data were preserved.")));
        }catch(Exception error) {
            var failures=new List<string>();
            foreach(var f in replaced.AsEnumerable().Reverse())try {
                string dest=Path.Combine(install,f.Path),saved=Path.Combine(backup,f.Path);
                if(f.Existed){File.Copy(saved,dest,true);CopyMode(saved,dest);}else File.Delete(dest);
            }catch(Exception e){failures.Add(f.Path+": "+e.Message);}
            string message=failures.Count==0?"The update failed; your previous build was restored. "+error.Message:"The update needs manual recovery from "+backup+". "+string.Join("; ",failures);
            File.WriteAllText(PendingPath(install),JsonSerializer.Serialize(new UpdateResult(work,false,message)));
            throw new UpdateException(message,error);
        }
    }
    static void CopyMode(string source,string target){if(!OperatingSystem.IsWindows())File.SetUnixFileMode(target,File.GetUnixFileMode(source));}
    public static string? FinishPending(string install) {
        string marker=PendingPath(install);
        if(!File.Exists(marker))return null;
        try {
            var result=JsonSerializer.Deserialize<UpdateResult>(File.ReadAllText(marker));if(result==null)return null;
            string work=Path.GetFullPath(result.Work);
            if(Path.GetDirectoryName(work)==Path.GetDirectoryName(Path.GetFullPath(install).TrimEnd(Path.DirectorySeparatorChar)) && Path.GetFileName(work).StartsWith(WorkPrefix(install),StringComparison.Ordinal) && result.Success) {
                // The helper may still be exiting on first start. Retry cleanup on
                // the next launch rather than deleting files underneath it.
                try{DeletePhysicalTree(work);File.Delete(marker);}catch(IOException){}catch(UnauthorizedAccessException){}
            }
            return result.Message;
        }catch(Exception e) when(e is IOException or JsonException or UnauthorizedAccessException){return "The previous update log could not be read: "+e.Message;}
    }
    static void DeletePhysicalTree(string path) {
        if(!Directory.Exists(path))return;
        if((File.GetAttributes(path)&FileAttributes.ReparsePoint)!=0)throw new IOException("Update cleanup refused a linked folder.");
        foreach(var item in Directory.EnumerateFileSystemEntries(path)) {
            if((File.GetAttributes(item)&FileAttributes.ReparsePoint)!=0)throw new IOException("Update cleanup refused a link.");
            if(Directory.Exists(item))DeletePhysicalTree(item);else File.Delete(item);
        }
        Directory.Delete(path);
    }
}
