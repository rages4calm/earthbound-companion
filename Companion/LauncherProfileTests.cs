using System.IO.Compression;
using System.Text.Json;

namespace EarthBoundCompanion;

static class LauncherProfileTests {
 internal static void Run(string reduxPack,string sourceGame,string scratch) {
  scratch=Path.GetFullPath(scratch);sourceGame=Path.GetFullPath(sourceGame);reduxPack=Path.GetFullPath(reduxPack);
  if(Directory.Exists(scratch))throw new IOException("Use a fresh isolated launcher test directory.");
  string previousRoot=Settings.Root;var checks=new List<string>();Settings.OverrideRoot=scratch;Settings.SessionDirectory=null;
  void Require(bool okay,string reason){if(!okay)throw new InvalidDataException(reason);}
  bool Refused(string backup,string session){try{SaveRecovery.Restore(backup,session,true);return false;}catch(InvalidDataException){return true;}}
  try {
   Directory.CreateDirectory(Settings.BaseGame);
   foreach(var name in new[]{"assets.pak","earthbound.exe","SDL2.dll"})File.Copy(Path.Combine(sourceGame,name),Path.Combine(Settings.BaseGame,name));
   Directory.CreateDirectory(ReduxProfileService.DirectoryPath);File.Copy(reduxPack,ReduxProfileService.Pack);
   string hash=StoryShuffle.HashFile(reduxPack);
   File.WriteAllText(Path.Combine(ReduxProfileService.DirectoryPath,"profile.json"),JsonSerializer.Serialize(new{contentId=ReduxProfileService.ContentId,assetPackSha256=hash}));
   var settings=new Settings{HqAudio=false,Fullscreen=false};settings.Save();string original=Settings.Game;
   ReduxProfileService.Select(settings);string redux=Settings.Game;
   var snapshot=SaveRecovery.Snapshot(redux);Require(snapshot.SessionId=="content:"+hash&&snapshot.AssetHash==hash,"Redux story snapshot identity failed");
   string phone=Path.Combine(redux,"saves","earthbound.srm");byte[] save=new byte[8192];save[11]=73;File.WriteAllBytes(phone,save);
   string backup=Settings.Backup(true,redux);
   using(var zip=ZipFile.OpenRead(backup))Require(zip.GetEntry("save-manifest.json")!=null&&zip.GetEntry("saves/earthbound.srm")!=null,"Redux story backup missing saves or identity");
   File.WriteAllBytes(phone,new byte[8192]);Require(SaveRecovery.Restore(backup,redux,true).Files==1&&File.ReadAllBytes(phone).SequenceEqual(save),"Redux phone restore failed");
   Require(Refused(backup,original),"Cross-edition restore accepted");
   string seedSession=StoryShuffle.Generate("launcher-profile-regression",new ShuffleOptions()).Session;
   Require(Refused(backup,seedSession),"Story backup restored into randomized adventure");
   settings=Settings.Load();Require(Settings.Game==redux,"Cold settings lost Redux story session");
   foreach(var edition in new[]{"redux","original","redux-seed","redux-original-title","original-original-title","redux-seed-original-title"}) {
    SeedRecord? seed=null;
    settings.OriginalTitleScreen=edition.EndsWith("original-title");
    if(edition.StartsWith("original")){settings.AssetPack="";settings.ReduxDevelopmentEnabled=false;settings.Save();}
    else {ReduxProfileService.Select(settings);if(edition.StartsWith("redux-seed"))seed=StoryShuffle.Read(Path.GetDirectoryName(seedSession)!);}
    using var process=GameLaunch.Start(settings,false,seed,["--headless","--skip-intro","--frames","300","--capture-state","20"]);
    if(!process.WaitForExit(30000)){process.Kill(true);throw new IOException("Native launcher test timed out");}
    Require(process.ExitCode==0,edition+" native process failed");
    string active=Settings.Game;string log=File.ReadAllText(Path.Combine(active,"game.log"));
    Require(log.Contains("PC replay checkpoint:"),edition+" native game-loop checkpoint absent");
    Require(log.Contains("Original EarthBound title presentation selected")==(!edition.StartsWith("original")&&settings.OriginalTitleScreen),edition+" title option did not reach the native player");
    checks.Add(edition+" production launch, pre-launch backup, native asset loading and clean exit");Settings.SessionDirectory=null;
   }
   Require(File.ReadAllBytes(phone).SequenceEqual(save),"Launch changed Redux phone save");
   checks.Add("Redux snapshot, phone backup/restore, cross-edition and cross-seed rejection, cold settings and phone-save preservation");
   File.WriteAllText(Path.Combine(scratch,"results.json"),JsonSerializer.Serialize(new{Passed=true,Checks=checks,FullPlaythroughVerified=false},Settings.JsonOptions));
  }finally{Settings.SessionDirectory=null;Settings.OverrideRoot=previousRoot;new Settings().ConfigureContentSession();}
 }
}
