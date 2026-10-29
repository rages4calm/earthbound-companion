// SPDX-License-Identifier: GPL-3.0-or-later
using System.Text;
using System.Text.Json;
using EarthBoundCompanion;

string root=Path.Combine(Path.GetTempPath(),"eb-port-test-"+Guid.NewGuid().ToString("N"));
Settings.OverrideRoot=root;
Directory.CreateDirectory(Settings.BaseGame);
Environment.SetEnvironmentVariable("COMPANION_ACHIEVEMENTS_DIR",Path.Combine(root,"Achievements"));
void Require(bool condition,string message){if(!condition)throw new Exception(message);}
// Synthetic support reports must retain real exceptions without attaching game data.
Directory.CreateDirectory(Settings.User);
string originalLog=Path.Combine(Settings.User,"original-setup.log");
string reduxLog=Path.Combine(Settings.User,"redux-setup.log");
File.WriteAllText(reduxLog,"STALE-REDUX-ERROR");
string fakeRom=Path.Combine(root,"private-owner-rom.sfc");File.WriteAllText(fakeRom,"PRIVATE-ROM-CONTENT");
var diagnostic=new SetupDiagnostics("Original",fakeRom);
diagnostic.Progress("ROM","Building assets");
File.WriteAllText(originalLog,"Traceback (most recent call last):\nPermissionError: "+fakeRom+"\n[PYI-11436:ERROR] Failed to execute script 'ebtools_setup_entry' due to unhandled exception!");
diagnostic.Finish(new IOException("Synthetic failure at "+root,new UnauthorizedAccessException("Denied "+fakeRom)));
Require(diagnostic.SavedPath!=null&&File.ReadAllText(diagnostic.SavedPath)==diagnostic.Report,"Automatic diagnostic report missing");
Require(diagnostic.Report.Contains("PermissionError")&&diagnostic.Report.Contains("UnauthorizedAccessException")&&diagnostic.Report.Contains("PYI-11436")&&diagnostic.Report.Contains("Building assets"),"Useful traceback or progress lost");
Require(!diagnostic.Report.Contains("STALE-REDUX-ERROR"),"Stale setup log leaked into new report");
Require(!diagnostic.Report.Contains(root,StringComparison.OrdinalIgnoreCase)&&!diagnostic.Report.Contains(fakeRom,StringComparison.OrdinalIgnoreCase)&&!diagnostic.Report.Contains("PRIVATE-ROM-CONTENT"),"Report exposed local paths or ROM contents");
// An unwritable UserData location must leave an in-memory report available to export.
string blockedRoot=Path.Combine(root,"blocked-report");Directory.CreateDirectory(blockedRoot);File.WriteAllText(Path.Combine(blockedRoot,"UserData"),"block directory creation");
Settings.OverrideRoot=blockedRoot;
var blockedDiagnostic=new SetupDiagnostics("Original");blockedDiagnostic.Finish(new IOException("Synthetic write failure"));
Require(blockedDiagnostic.SavedPath==null&&blockedDiagnostic.Report.Contains("Synthetic write failure"),"Report lost when log directory unwritable");
Settings.OverrideRoot=root;
Console.WriteLine("Setup reports preserve tracebacks, redact paths, exclude stale logs, and survive log-write failure.");
// SteamOS/Linux may redirect home, XDG ancestors, or the app-data root.
// Profile children must still be physical and must never reach an outside file.
if(!OperatingSystem.IsWindows()) {
 string sandbox=Path.Combine(root,"redirected-path-test");
 string real=Path.Combine(sandbox,"real");Directory.CreateDirectory(real);
 string parentLink=Path.Combine(sandbox,"home-link");Directory.CreateSymbolicLink(parentLink,real);
 string data=Path.Combine(parentLink,".local","share","EarthBoundCompanionPreview");
 Directory.CreateDirectory(data);
 try {
  Settings.OverrideRoot=data;
  ReduxStoryUpgrade.Physical(ReduxProfileService.DirectoryPath);
  Require(!Directory.Exists(ReduxProfileService.DirectoryPath),"Path validation created a profile");
  string rootLink=Path.Combine(sandbox,"data-link");Directory.CreateSymbolicLink(rootLink,data);
  Settings.OverrideRoot=rootLink;
  ReduxStoryUpgrade.Physical(Path.Combine(rootLink,"Profiles","future-profile"));
  string outside=Path.Combine(sandbox,"outside");Directory.CreateDirectory(outside);
  string sentinel=Path.Combine(outside,"sentinel");File.WriteAllText(sentinel,"unchanged");
  string child=Path.Combine(rootLink,"Profiles");Directory.CreateSymbolicLink(child,outside);
  try{ReduxStoryUpgrade.Physical(Path.Combine(child,"future-profile"));throw new Exception("Redirected profile accepted");}
  catch(IOException){}
  Require(File.ReadAllText(sentinel)=="unchanged","Validation modified an outside file");
  // A sibling outside the configured root does not inherit its exemption.
  try{ReduxStoryUpgrade.Physical(Path.Combine(parentLink,"unrelated"));throw new Exception("Unrelated redirected path accepted");}
  catch(IOException){}
  Directory.Delete(child);Directory.Delete(rootLink);
 } finally {Settings.OverrideRoot=root;Directory.Delete(parentLink);}
 Console.WriteLine("Unix data-root symlinks accepted; redirected profile children rejected.");
}
var achievementView=AchievementProfiles.Read("original");
Require(achievementView.Entries.Count==46&&achievementView.Entries.All(e=>!e.Unlocked),"Missing profile should show full locked set");
Require(achievementView.Entries.Select(e=>e.Id).Distinct().Count()==46&&achievementView.Entries.All(e=>AchievementProfiles.Categories.Contains(e.Category)),"Catalog IDs or categories invalid");
Directory.CreateDirectory(AchievementProfiles.Root);
string achievementFile=Path.Combine(AchievementProfiles.Root,"earthbound-original.json");
File.WriteAllText(achievementFile,"""{"schema":1,"gameId":"earthbound","edition":"original","achievements":[{"id":"first-fight","progress":1,"unlockedAt":1700000000},{"id":"getting-the-hang","progress":3,"unlockedAt":0}]}""");
achievementView=AchievementProfiles.Read("original");
Require(achievementView.Entries.Count(e=>e.Unlocked)==1&&achievementView.Entries.Single(e=>e.Id=="getting-the-hang").Progress==3,"Native achievement profile not parsed correctly");
Require(AchievementProfiles.Read("redux").Entries.All(e=>!e.Unlocked),"Edition progress leaked");
File.WriteAllText(achievementFile,"""{"schema":2,"gameId":"earthbound","edition":"original","achievements":[]}""");
string invalidAchievement=File.ReadAllText(achievementFile);
Require(AchievementProfiles.Read("original").Message.Contains("left untouched")&&File.ReadAllText(achievementFile)==invalidAchievement,"Unsupported achievement profile was not protected");
File.WriteAllText(achievementFile,"""{"schema":1,"gameId":"earthbound","edition":"original","achievements":[{"id":"first-fight","progress":1,"unlockedAt":0}]}""");
Require(AchievementProfiles.Read("original").Message.Contains("left untouched"),"Invalid unlock consistency accepted");
var settings=new Settings{Width=2560,Height=1440,Sprint=2,Aspect=2,ShaderPreset="abc\ndef",AchievementSound=false};
settings.WriteEngine(Settings.BaseGame);
byte[] binary=File.ReadAllBytes(Settings.PathTo("settings.dat"));
Require(binary.Length==16&&Encoding.ASCII.GetString(binary,0,4)=="EBST"&&binary[4]==5&&binary[5]==2&&binary[14]==2,"Engine settings ABI changed");
settings.Validate();Require(settings.ShaderPreset=="","Shader INI delimiter accepted");
string ini=File.ReadAllText(Settings.PathTo("earthbound.ini"));
Require(ini.Contains("width=2560")&&ini.Contains("exp_multiplier=1")&&ini.Contains("key.20=6"),"Native configuration missing");
Require(ini.Contains("achievement_sound=0"),"Achievement sound preference missing from native configuration");
settings.Save();Require(Settings.Load().Sprint==2&&Settings.Load().Width==2560,"Settings round trip failed");
Require(!Settings.Load().AchievementSound&&new Settings().AchievementSound,"Achievement sound preference round trip/default failed");
 Require(new Settings().ShowTouchControls&&JsonSerializer.Deserialize<Settings>("{}")!.ShowTouchControls,"Older settings should retain visible touch controls");
 settings.ShowTouchControls=false;settings.Save();Require(!Settings.Load().ShowTouchControls,"Hidden touch-control preference did not persist");
 settings.Preset("Classic");Require(!settings.ShowTouchControls,"Display presets should preserve handheld touch-control preference");
Require(Settings.Root==root&&Settings.User.StartsWith(root),"Test root escaped");
Require(!HostRuntime.Executable("earthbound").StartsWith(root),"Data folder used as executable search path");
File.WriteAllBytes(Path.Combine(Settings.BaseGame,"assets.pak"),"Synthetic test fixture; no game content"u8.ToArray());
Directory.CreateDirectory(Path.Combine(Settings.BaseGame,"saves"));
var phone=Enumerable.Range(0,8192).Select(i=>(byte)(i%251)).ToArray();
string phonePath=Path.Combine(Settings.BaseGame,"saves","earthbound.srm");File.WriteAllBytes(phonePath,phone);
string backup=Settings.Backup(true);
File.WriteAllBytes(phonePath,new byte[8192]);
var restored=SaveRecovery.Restore(backup,Settings.BaseGame,true);
Require(restored.Files==1&&File.ReadAllBytes(phonePath).SequenceEqual(phone),"Phone-save backup/restore failed");
Require(File.Exists(restored.PreviousBackup),"Restore did not protect previous save");
Require(StoryShuffle.CleanSeed("  abc  ")=="abc","Seed normalization changed");
try{new ShuffleOptions{Mode="invalid"}.Validate();throw new Exception("Invalid recipe accepted");}catch(InvalidDataException){}
if(args.Length>0){
 foreach(string packPath in args){
  byte[] source=File.ReadAllBytes(packPath);var hashes=new List<string>();
  foreach(string mode in new[]{"Balanced","Surprise"})foreach(string seed in new[]{"ports-a","ports-b"}) {
   var options=new ShuffleOptions{Mode=mode};var first=StoryShuffle.Build(source,seed,options);var second=StoryShuffle.Build(source,seed,options);
   StoryShuffleV4.Validate(source,first.Pack,options);
   Require(first.Pack.SequenceEqual(second.Pack),"Seed nondeterministic");hashes.Add(StoryShuffle.Hash(first.Pack));
  }
  Require(hashes.Distinct().Count()==4,"Seed/mode domains collapsed");
  Console.WriteLine(JsonSerializer.Serialize(new {Content=ProgressionGuard.CheckBase(source).ContentId,SourceHash=StoryShuffle.Hash(source),RecipeOutputHashes=hashes}));
 }
 if(File.Exists(HostRuntime.Executable("earthbound"))) {
  File.Move(phonePath,phonePath+".synthetic-fixture");
  File.Copy(args[0],Path.Combine(Settings.BaseGame,"assets.pak"),true);
  foreach(string path in args) {
   settings.AssetPack=Path.GetFullPath(path);settings.ReduxDevelopmentEnabled=ProgressionGuard.CheckBase(File.ReadAllBytes(path)).ContentId==ReduxProfileService.ContentId;
   settings.ConfigureContentSession();
   using var game=GameLaunch.Start(settings,false,null,["--headless","--skip-intro","--frames","4"]);
   Require(game.WaitForExit(30000),"Native launch timeout");Require(game.ExitCode==0,"Native launch failed");Settings.SessionDirectory=null;
  }
  Console.WriteLine("Actual native headless launch: Original and Redux PASS (no campaign claimed)");
 }
}
Console.WriteLine(JsonSerializer.Serialize(new{Passed=true,SettingsAbi=5,PhoneSaveBytes=8192,RootIsolated=true,Checked="paths, settings round-trip, INI validation, phone-save recovery, recipe validation",GameplayTested=false}));
