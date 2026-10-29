using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;

namespace EarthBoundCompanion;

// Text only: never attach ROMs, packs, settings, saves, or arbitrary directories.
internal sealed class SetupDiagnostics {
 static readonly string[] Logs=["original-setup.log","redux-setup.log","rom-setup.log","msu-setup.log"];
 readonly string root=Settings.Root,user=Settings.User;
 readonly string? rom;
 readonly Dictionary<string,DateTime> previous=new();
 readonly StringBuilder text=new();
 internal string Report{get;private set;}="";
 internal string? SavedPath{get;private set;}
 internal SetupDiagnostics(string mode,string? romPath=null) {
  rom=romPath;
  text.AppendLine("EarthBound Companion setup diagnostic report").AppendLine($"UTC: {DateTimeOffset.UtcNow:O}")
   .AppendLine($"Launcher: {typeof(SetupDiagnostics).Assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion ?? typeof(SetupDiagnostics).Assembly.GetName().Version?.ToString()}")
   .AppendLine($"Application: {Assembly.GetEntryAssembly()?.GetName().Name} {Assembly.GetEntryAssembly()?.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion}")
   .AppendLine($"OS: {RuntimeInformation.OSDescription}").AppendLine($"Architecture: {RuntimeInformation.OSArchitecture}; process {RuntimeInformation.ProcessArchitecture}")
   .AppendLine($"Runtime: {RuntimeInformation.FrameworkDescription}").AppendLine($"Setup: {mode}");
  if(rom!=null)try{text.AppendLine($"ROM size: {new FileInfo(rom).Length} bytes");}catch(Exception e)when(e is IOException or UnauthorizedAccessException or ArgumentException){text.AppendLine("ROM size unavailable");}
  foreach(string name in Logs)previous[name]=File.GetLastWriteTimeUtc(Path.Combine(user,name));
 }
 internal void Progress(string stage,string detail)=>text.AppendLine($"[{DateTimeOffset.UtcNow:O}] {stage}: {detail}");
 internal void Finish(Exception? error=null,string? warning=null) {
  text.AppendLine(error==null?"Result: "+(warning??"Completed"):"Result: Failed\n"+error);
  foreach(string name in Logs) {
   string path=Path.Combine(user,name);
   try {
    if(!File.Exists(path)||File.GetLastWriteTimeUtc(path)==previous[name])continue;
    // Bound the report and avoid reading an unexpectedly huge log into memory.
    using var stream=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite);
    const int limit=256*1024;
    if(stream.Length>limit){stream.Seek(-limit,SeekOrigin.End);text.AppendLine("[Log truncated to final 256 KiB]");}
    using var reader=new StreamReader(stream);
    text.AppendLine("\n--- "+name+" ---").AppendLine(reader.ReadToEnd());
   }catch(Exception e)when(e is IOException or UnauthorizedAccessException){text.AppendLine($"Could not read {name}: {e.GetType().Name}");}
  }
  Report=Redact(text.ToString());
  try{Directory.CreateDirectory(user);SavedPath=Path.Combine(user,"setup-diagnostics.txt");File.WriteAllText(SavedPath,Report);}
  catch(Exception e)when(e is IOException or UnauthorizedAccessException){SavedPath=null;}
 }
 string Redact(string value) {
  var paths=new[]{(rom,"<ROM>"),(root,"<COMPANION>"),(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),"<HOME>"),(Path.GetTempPath().TrimEnd(Path.DirectorySeparatorChar),"<TEMP>")};
  foreach(var (path,label) in paths.Where(p=>!string.IsNullOrEmpty(p.Item1)).OrderByDescending(p=>p.Item1!.Length)) {
   value=value.Replace(path!,label,StringComparison.OrdinalIgnoreCase).Replace(path!.Replace('\\','/'),label,StringComparison.OrdinalIgnoreCase).Replace(path.Replace('\\','/').Replace("/","\\\\"),label,StringComparison.OrdinalIgnoreCase);
  }
  return value;
 }
}
