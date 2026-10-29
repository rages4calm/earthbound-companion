using System.Diagnostics;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text.Json;

namespace EarthBoundCompanion;

internal sealed record SetupProgress(string Stage, string Detail, long Done=0, long Total=0);

internal static class SetupService {
 const string UsaRomSha256="A8FE2226728002786D68C27DDDDF0B90A894DB52E4DFE268FDF72A68CAE5F02E";
 static readonly HttpClient Http=new(){Timeout=TimeSpan.FromMinutes(10)};

 internal static bool DataReady=>File.Exists(Path.Combine(Settings.BaseGame,"assets.pak"));
 internal static bool OriginalMovementUpdateNeeded {
  get {
   if(!DataReady)return false;
   try {
    byte[] pack=File.ReadAllBytes(Path.Combine(Settings.BaseGame,"assets.pak"));
    StoryShuffle.ValidatePack(pack);
    return !StoryShuffle.Table(pack,"US/events/bank_c3_scripts_combined.bin").StartsWith("EBMVBN01"u8);
   } catch(Exception e)when(e is IOException or UnauthorizedAccessException or InvalidDataException or ArgumentException or OverflowException or KeyNotFoundException){return true;}
  }
 }

 internal static async Task<SetupResult> InstallAsync(string? romPath,bool installMsu,IProgress<SetupProgress>? progress=null,CancellationToken cancel=default) {
  bool createdSeed=false;
  if(!DataReady||(!string.IsNullOrWhiteSpace(romPath)&&OriginalMovementUpdateNeeded)) {
   if(string.IsNullOrWhiteSpace(romPath))throw new ArgumentException("Choose your EarthBound (USA) ROM first.");
   progress?.Report(new("ROM","Checking your ROM…"));
   await ValidateRomAsync(romPath,cancel);
   await BuildAssetsAsync(romPath,progress,cancel);
   try {StoryShuffle.Generate("Tonight in Onett",new ShuffleOptions());createdSeed=true;}catch(IOException){}catch(InvalidDataException){}
  }
  int tracks=0;long bytes=0;
  if(installMsu)(tracks,bytes)=await InstallMsuAsync(progress,cancel);
  return new(tracks,bytes,createdSeed);
 }

 // Build playable data before attempting optional music. A remote music outage must
 // never prevent an otherwise valid Original/Redux installation from completing.
 internal static Task<SetupResult> InstallGameAsync(string? romPath,bool installMsu,bool redux,IProgress<SetupProgress>? progress=null,CancellationToken cancel=default)=>
  SetupWorkflow.RunAsync(async()=>{
   var result=await InstallAsync(romPath,false,progress,cancel);
   if(redux)await ReduxProfileService.BuildAsync(romPath!,progress,cancel);
   return result;
  },installMsu?()=>InstallMsuAsync(progress,cancel):null,cancel);

 static async Task ValidateRomAsync(string path,CancellationToken cancel) {
  var info=new FileInfo(path);if(!info.Exists)throw new IOException("That ROM file no longer exists.");
  if(info.Length is not (3145728 or 3146240))throw new InvalidDataException("Use a clean EarthBound (USA) ROM. The selected file has the wrong size.");
  await using var stream=File.OpenRead(path);if(info.Length==3146240)stream.Position=512;
  using var sha=SHA256.Create();byte[] hash=await sha.ComputeHashAsync(stream,cancel);
  if(!Convert.ToHexString(hash).Equals(UsaRomSha256,StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("This is not the supported clean EarthBound (USA) ROM. No files were changed.");
 }

 static async Task BuildAssetsAsync(string romPath,IProgress<SetupProgress>? progress,CancellationToken cancel) {
  string helper=HostRuntime.Executable("ebtools-setup");
  if(!File.Exists(helper))throw new IOException("The ROM setup helper is missing. Re-extract the tester ZIP and try again.");
  Directory.CreateDirectory(Settings.BaseGame);string target=Path.Combine(Settings.BaseGame,"assets.pak"),temp=target+".setup-"+Guid.NewGuid().ToString("N");
  progress?.Report(new("ROM","Building native game data from your ROM. This may take a few minutes…"));
  var start=new ProcessStartInfo(helper){WorkingDirectory=Settings.BaseGame,UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true};
  start.ArgumentList.Add(Path.GetFullPath(romPath));start.ArgumentList.Add("--out");start.ArgumentList.Add(temp);
  try {
   using var process=Process.Start(start)??throw new IOException("The ROM setup helper did not start.");
   using var stopped=cancel.Register(()=>{try{if(!process.HasExited)process.Kill(true);}catch(InvalidOperationException){}catch(System.ComponentModel.Win32Exception){}});
   var stdout=process.StandardOutput.ReadToEndAsync();var stderr=process.StandardError.ReadToEndAsync();
   await process.WaitForExitAsync();cancel.ThrowIfCancellationRequested();string output=(await stdout)+Environment.NewLine+(await stderr);
   // PyInstaller appends a generic failure banner after the useful traceback.
   // Keep both streams so support can diagnose the original exception.
   string log=Path.Combine(Settings.User,"original-setup.log");
   bool logged=false;
   try {
    Directory.CreateDirectory(Settings.User);
    await File.WriteAllTextAsync(log,$"{DateTimeOffset.UtcNow:O}\nPlatform: {System.Runtime.InteropServices.RuntimeInformation.OSDescription}\nHelper exit code: {process.ExitCode}\n{output}",cancel);
    logged=true;
   } catch(IOException){}catch(UnauthorizedAccessException){}
   if(process.ExitCode!=0) {
    string detail=output.Split('\n').Select(line=>line.Trim()).LastOrDefault(line=>line.Length!=0&&!line.StartsWith("[PYI-",StringComparison.Ordinal))??"The ROM setup helper stopped unexpectedly.";
    throw new InvalidDataException("Game-data setup failed. "+detail+(logged?"\nFull details: "+log:""));
   }
   if(!File.Exists(temp))throw new InvalidDataException("Game-data setup finished without creating an asset pack.");
   byte[] pack=await File.ReadAllBytesAsync(temp,cancel);ProgressionGuard.CheckBase(pack);
   File.Move(temp,target,true);
  } finally {if(File.Exists(temp))File.Delete(temp);}
 }

 internal static MsuEntry[] LoadMsuManifest() {
  using var stream=typeof(SetupService).Assembly.GetManifestResourceStream("EarthBoundCompanion.msu-manifest.json")
   ?? typeof(SetupService).Assembly.GetManifestResourceNames().Where(n=>n.EndsWith("msu-manifest.json")).Select(n=>typeof(SetupService).Assembly.GetManifestResourceStream(n)).FirstOrDefault()
   ?? throw new InvalidDataException("The soundtrack manifest is missing.");
  return JsonSerializer.Deserialize<MsuEntry[]>(stream)??throw new InvalidDataException("The soundtrack manifest is empty.");
 }

 static async Task<(int Tracks,long Bytes)> InstallMsuAsync(IProgress<SetupProgress>? progress,CancellationToken cancel) {
  try{return await DownloadMsuAsync(progress,cancel);}
  catch(Exception e)when(e is not OperationCanceledException){
   // Logging must not turn an optional download failure into a game-setup failure.
   try{Directory.CreateDirectory(Settings.User);await File.WriteAllTextAsync(Path.Combine(Settings.User,"msu-setup.log"),DateTimeOffset.UtcNow+Environment.NewLine+e+Environment.NewLine,cancel);}catch(IOException){}catch(UnauthorizedAccessException){}
   throw;
  }
 }

 static async Task<(int Tracks,long Bytes)> DownloadMsuAsync(IProgress<SetupProgress>? progress,CancellationToken cancel) {
  var entries=LoadMsuManifest();long total=entries.Sum(e=>e.Size),done=0;int count=0;string folder=Path.Combine(Settings.Root,"msu");Directory.CreateDirectory(folder);
  var downloader=new MsuDownloader(Http,MsuDownloader.LoadSources(Path.Combine(Settings.Root,"msu-sources.json")));
  foreach(var entry in entries) {
   cancel.ThrowIfCancellationRequested();string target=Path.Combine(folder,entry.Name);
   if(await MatchesAsync(target,entry,cancel)){done+=entry.Size;count++;progress?.Report(new("MSU",$"Verified {count} of {entries.Length} tracks",done,total));continue;}
   progress?.Report(new("MSU",$"Downloading track {count+1} of {entries.Length}",done,total));
   await downloader.DownloadAsync(entry,target,(detail,bytes)=>progress?.Report(new("MSU",$"Track {count+1}/{entries.Length}: {detail}",done+bytes,total)),cancel);
   done+=entry.Size;count++;
  }
  return(count,total);
 }

 static async Task<bool> MatchesAsync(string path,MsuEntry entry,CancellationToken cancel) {
  var info=new FileInfo(path);if(!info.Exists||info.Length!=entry.Size)return false;
  await using var stream=File.OpenRead(path);using var md5=MD5.Create();byte[] hash=await md5.ComputeHashAsync(stream,cancel);
  return Convert.ToHexString(hash).Equals(entry.Md5,StringComparison.OrdinalIgnoreCase);
 }
}
