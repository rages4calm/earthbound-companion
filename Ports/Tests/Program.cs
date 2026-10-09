// SPDX-License-Identifier: GPL-3.0-or-later
using System.Text;
using System.Text.Json;
using EarthBoundCompanion;

string root=Path.Combine(Path.GetTempPath(),"eb-port-test-"+Guid.NewGuid().ToString("N"));
Settings.OverrideRoot=root;
Directory.CreateDirectory(Settings.BaseGame);
void Require(bool condition,string message){if(!condition)throw new Exception(message);}
var settings=new Settings{Width=2560,Height=1440,Sprint=2,Aspect=2,ShaderPreset="abc\ndef"};
settings.WriteEngine(Settings.BaseGame);
byte[] binary=File.ReadAllBytes(Settings.PathTo("settings.dat"));
Require(binary.Length==16&&Encoding.ASCII.GetString(binary,0,4)=="EBST"&&binary[4]==5&&binary[5]==2&&binary[14]==2,"Engine settings ABI changed");
settings.Validate();Require(settings.ShaderPreset=="","Shader INI delimiter accepted");
string ini=File.ReadAllText(Settings.PathTo("earthbound.ini"));
Require(ini.Contains("width=2560")&&ini.Contains("exp_multiplier=1")&&ini.Contains("key.20=6"),"Native configuration missing");
settings.Save();Require(Settings.Load().Sprint==2&&Settings.Load().Width==2560,"Settings round trip failed");
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
}
Console.WriteLine(JsonSerializer.Serialize(new{Passed=true,SettingsAbi=5,PhoneSaveBytes=8192,RootIsolated=true,Checked="paths, settings round-trip, INI validation, phone-save recovery, recipe validation",GameplayTested=false}));
