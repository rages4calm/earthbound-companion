using System.Diagnostics;
using System.Text.Json;

namespace EarthBoundCompanion;

static class ReduxProfileService {
 internal const string ContentId="maternalbound-redux-897d0083";
 internal static string DirectoryPath=>Path.Combine(Settings.Root,"Profiles",ContentId);
 internal static string Pack=>Path.Combine(DirectoryPath,"assets.pak");
 internal static bool Ready=>File.Exists(Pack)&&File.Exists(Path.Combine(DirectoryPath,"profile.json"));
 internal static void Select(Settings settings){
  var policy=ProgressionGuard.CheckBase(File.ReadAllBytes(Pack));
  using var profile=JsonDocument.Parse(File.ReadAllText(Path.Combine(DirectoryPath,"profile.json")));
  if(policy.ContentId!=ContentId||profile.RootElement.GetProperty("contentId").GetString()!=ContentId||
     !profile.RootElement.GetProperty("assetPackSha256").GetString()!.Equals(policy.BaseHash,StringComparison.OrdinalIgnoreCase))
   throw new InvalidDataException("Redux profile metadata does not match its audited asset pack.");
  settings.AssetPack=Pack;settings.ReduxDevelopmentEnabled=true;settings.Save();
 }
 internal static bool AllowDevelopmentLaunch(Settings settings){
  var bytes=File.ReadAllBytes(settings.Pak);
  ProgressionPolicy policy;
  try{policy=ProgressionGuard.CheckBase(bytes);}catch(InvalidDataException){return false;}
  if(policy.ContentId!=ContentId)return false;
  if(!settings.ReduxDevelopmentEnabled)throw new InvalidDataException("Select the Redux development profile from Game Mode before playing. It uses separate saves and has not passed a full playthrough.");
  return true;
 }
 internal static async Task BuildAsync(string rom,IProgress<SetupProgress>? progress=null,CancellationToken cancel=default){
  if(Ready){progress?.Report(new("Redux","The Redux development profile is already built."));return;}
  if(Directory.Exists(DirectoryPath))throw new IOException("An incomplete Redux profile exists. Preserve its diagnostics and choose a fresh profile directory before rebuilding.");
  string helper=Path.Combine(Settings.BaseGame,"redux-setup.exe");
  if(!File.Exists(helper))throw new IOException("The Redux setup helper is missing. Use the complete Redux development package.");
  var start=new ProcessStartInfo(helper){WorkingDirectory=Settings.Root,UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true};
  foreach(var argument in new[]{"--rom",Path.GetFullPath(rom),"--base-assets",Path.Combine(Settings.BaseGame,"assets.pak"),"--output-directory",DirectoryPath})start.ArgumentList.Add(argument);
  using var process=Process.Start(start)??throw new IOException("Redux setup did not start.");
  using var stopped=cancel.Register(()=>{try{if(!process.HasExited)process.Kill(true);}catch(InvalidOperationException){}catch(System.ComponentModel.Win32Exception){}});
  string log=Path.Combine(Settings.User,"redux-setup.log");Directory.CreateDirectory(Settings.User);
  var errors=process.StandardError.ReadToEndAsync();
  var lines=new List<string>();
  while(await process.StandardOutput.ReadLineAsync() is string line){
   lines.Add(line);
   try{using var data=JsonDocument.Parse(line);if(data.RootElement.TryGetProperty("stage",out var stage))progress?.Report(new("Redux","Building Redux: "+stage.GetString()!.Replace('-',' ')));}catch(JsonException){}
  }
  await process.WaitForExitAsync();string stderr=await errors;File.WriteAllText(log,string.Join(Environment.NewLine,lines)+Environment.NewLine+stderr);
  cancel.ThrowIfCancellationRequested();
  if(process.ExitCode!=0||!Ready)throw new InvalidDataException("Redux setup failed. Existing games and saves are unchanged. See UserData/redux-setup.log.");
  progress?.Report(new("Redux","Redux development profile built. Full playthrough is still unverified."));
 }
 internal static void Test(string pack,string scratch){
  string root=Path.GetFullPath(scratch);if(Directory.Exists(root))throw new IOException("Use a fresh test directory.");
  string previousRoot=Settings.Root;Settings.OverrideRoot=root;Settings.SessionDirectory=null;
  try{
   Directory.CreateDirectory(Settings.BaseGame);Directory.CreateDirectory(DirectoryPath);File.Copy(pack,Pack);
   var policy=ProgressionGuard.CheckBase(File.ReadAllBytes(Pack));
   if(policy.ContentId!=ContentId)throw new InvalidDataException("Use the audited Redux pack.");
   File.WriteAllText(Path.Combine(DirectoryPath,"profile.json"),JsonSerializer.Serialize(new {contentId=ContentId,assetPackSha256=policy.BaseHash}));
   var original=new Settings();original.Save();string originalGame=Settings.Game;
   File.WriteAllText(Path.Combine(originalGame,"saves","sentinel.srm"),"original-save");
   Select(original);string reduxGame=Settings.Game;
   if(reduxGame==originalGame||!AllowDevelopmentLaunch(original))throw new InvalidDataException("Redux profile did not isolate its session.");
   File.WriteAllText(Path.Combine(reduxGame,"saves","sentinel.srm"),"redux-save");
   var cold=Settings.Load();if(Settings.Game!=reduxGame||!cold.ReduxDevelopmentEnabled)throw new InvalidDataException("Cold profile restore failed.");
   Settings.SessionDirectory=Path.Combine(root,"seed-session");cold.Save();if(Settings.Game!=Settings.SessionDirectory)throw new InvalidDataException("Seed session did not override story session.");Settings.SessionDirectory=null;
   cold.AssetPack="";cold.ReduxDevelopmentEnabled=false;cold.Save();
   if(Settings.Game!=originalGame||File.ReadAllText(Path.Combine(originalGame,"saves","sentinel.srm"))!="original-save"||File.ReadAllText(Path.Combine(reduxGame,"saves","sentinel.srm"))!="redux-save")throw new InvalidDataException("Profile switch changed a save.");
   File.WriteAllText(Path.Combine(root,"results.json"),JsonSerializer.Serialize(new {Passed=true,Checks=new[]{"Exact Redux content identity","Development launch flag","Original/Redux save isolation","Cold profile restore","Seed session override","Return to original preserves both saves"},FullPlaythroughVerified=false},Settings.JsonOptions));
  }finally{Settings.SessionDirectory=null;Settings.OverrideRoot=previousRoot;new Settings().ConfigureContentSession();}
 }
}
