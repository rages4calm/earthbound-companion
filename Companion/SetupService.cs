using System.Diagnostics;
using System.Net.Http;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace EarthBoundCompanion;

internal sealed record SetupProgress(string Stage, string Detail, long Done=0, long Total=0);
internal sealed record SetupResult(int MsuTracks, long MsuBytes, bool CreatedStarterSeed);
internal sealed record MsuEntry(
 [property:JsonPropertyName("name")] string Name,
 [property:JsonPropertyName("size")] string SizeText,
 [property:JsonPropertyName("md5")] string Md5,
 [property:JsonPropertyName("sha1")] string Sha1) {
 public long Size=>long.Parse(SizeText,System.Globalization.CultureInfo.InvariantCulture);
}

internal static class SetupService {
 const string UsaRomSha256="A8FE2226728002786D68C27DDDDF0B90A894DB52E4DFE268FDF72A68CAE5F02E";
 const string MsuBase="https://archive.org/download/earthbound-msu-1-pack/";
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
   if(process.ExitCode!=0)throw new InvalidDataException("Game-data setup failed. "+output.Trim().Split('\n').LastOrDefault()?.Trim());
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
  var entries=LoadMsuManifest();long total=entries.Sum(e=>e.Size),done=0;int count=0;string folder=Path.Combine(Settings.Root,"msu");Directory.CreateDirectory(folder);
  foreach(var entry in entries) {
   cancel.ThrowIfCancellationRequested();string target=Path.Combine(folder,entry.Name);
   if(await MatchesAsync(target,entry,cancel)){done+=entry.Size;count++;progress?.Report(new("MSU",$"Verified {count} of {entries.Length} tracks",done,total));continue;}
   string part=target+".part";if(File.Exists(part))File.Delete(part);
   progress?.Report(new("MSU",$"Downloading track {count+1} of {entries.Length}",done,total));
   try {
    using var response=await Http.GetAsync(MsuBase+Uri.EscapeDataString(entry.Name),HttpCompletionOption.ResponseHeadersRead,cancel);response.EnsureSuccessStatusCode();
    await using var input=await response.Content.ReadAsStreamAsync(cancel);
    await using(var output=new FileStream(part,FileMode.CreateNew,FileAccess.Write,FileShare.None,262144,true)){
     byte[] buffer=new byte[262144];int read;long fileDone=0;
     while((read=await input.ReadAsync(buffer,cancel))>0){await output.WriteAsync(buffer.AsMemory(0,read),cancel);fileDone+=read;progress?.Report(new("MSU",$"Downloading track {count+1} of {entries.Length}",done+fileDone,total));}
     await output.FlushAsync(cancel);
    }
    if(!await MatchesAsync(part,entry,cancel))throw new InvalidDataException("Soundtrack download failed its checksum: "+entry.Name);
    File.Move(part,target,true);done+=entry.Size;count++;
   } finally {if(File.Exists(part))File.Delete(part);}
  }
  return(count,total);
 }

 static async Task<bool> MatchesAsync(string path,MsuEntry entry,CancellationToken cancel) {
  var info=new FileInfo(path);if(!info.Exists||info.Length!=entry.Size)return false;
  await using var stream=File.OpenRead(path);using var md5=MD5.Create();byte[] hash=await md5.ComputeHashAsync(stream,cancel);
  return Convert.ToHexString(hash).Equals(entry.Md5,StringComparison.OrdinalIgnoreCase);
 }
}
