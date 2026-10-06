using System.Text.Json;

namespace EarthBoundCompanion;

static class ReduxUpgradeTests {
 internal static void Run(string oldPath,string newPath,string checkpointPath,string phonePath,string scratch) {
  scratch=Path.GetFullPath(scratch);if(Directory.Exists(scratch))throw new IOException("Use a fresh isolated upgrade-test directory.");
  var inputPaths=new[]{oldPath,newPath,checkpointPath,phonePath}.Select(Path.GetFullPath).ToArray();
  var inputHashes=inputPaths.ToDictionary(p=>p,StoryShuffle.HashFile);
  byte[] oldPack=File.ReadAllBytes(oldPath),newPack=File.ReadAllBytes(newPath),checkpoint=File.ReadAllBytes(checkpointPath),phone=File.ReadAllBytes(phonePath);
  string oldHash=StoryShuffle.Hash(oldPack),newHash=StoryShuffle.Hash(newPack);
  var checks=new List<string>();
  void Require(bool value,string reason){if(!value)throw new InvalidDataException(reason);checks.Add(reason);}
  void Refused(Action action,string reason){bool rejected=false;try{action();}catch(Exception e)when(e is IOException or InvalidDataException){rejected=true;}Require(rejected,reason);}
  Require(ReduxStoryUpgrade.Validate(oldPack,newPack)==oldHash,"Exact reviewed pair and per-asset differences accepted");
  Require(phone.Length==8192&&SaveRecovery.ValidQuick(checkpoint),"Read-only actual phone and format-16 F6 inputs valid");
  byte[] bad=(byte[])newPack.Clone();bad[^1]^=1;Refused(()=>ReduxStoryUpgrade.Validate(oldPack,bad),"Unknown changed pack refused");
  Refused(()=>ReduxStoryUpgrade.Validate(newPack,oldPack),"Reverse upgrade refused");
  string? priorOverride=Settings.OverrideRoot;string? priorSession=Settings.SessionDirectory;
  Directory.CreateDirectory(scratch);string source=Path.Combine(scratch,"previous"),target=Path.Combine(scratch,"current");
  string SourceSaves()=>Path.Combine(source,"UserData","ContentProfiles",oldHash,"Game","saves");
  string TargetSaves()=>Path.Combine(target,"UserData","ContentProfiles",newHash,"Game","saves");
  try {
   Settings.OverrideRoot=target;Settings.SessionDirectory=null;
   string priorPack=Path.Combine(source,"Profiles",ReduxProfileService.ContentId,"assets.pak");Directory.CreateDirectory(Path.GetDirectoryName(priorPack)!);File.WriteAllBytes(priorPack,oldPack);
   Directory.CreateDirectory(ReduxProfileService.DirectoryPath);File.WriteAllBytes(ReduxProfileService.Pack,newPack);
   Refused(()=>ReduxStoryUpgrade.Import(source),"Missing story saves refused");
   Require(ReduxStoryUpgrade.CopyStorySaves(source,oldHash,newHash,false)==0,"Setup without earlier saves copies no files");
   Directory.CreateDirectory(SourceSaves());File.WriteAllBytes(Path.Combine(SourceSaves(),"earthbound.srm"),phone);
   File.WriteAllBytes(Path.Combine(SourceSaves(),"quicksave_1.bin.0"),checkpoint);File.WriteAllBytes(Path.Combine(SourceSaves(),"quicksave_1.bin.1"),checkpoint);
   string seed=Path.Combine(source,"UserData","Seeds","preserved-seed","Game","saves");Directory.CreateDirectory(seed);File.WriteAllBytes(Path.Combine(seed,"earthbound.srm"),phone);
   File.WriteAllText(Path.Combine(SourceSaves(),"unrelated.txt"),"do not import");
   var before=Directory.GetFiles(source,"*",SearchOption.AllDirectories).ToDictionary(p=>p,StoryShuffle.HashFile);
   Require(ReduxStoryUpgrade.Import(source)==3,"Phone and two F6 checkpoint generations imported");
   Require(File.ReadAllBytes(Path.Combine(TargetSaves(),"earthbound.srm")).SequenceEqual(phone),"Phone bytes copied exactly");
   Require(new[]{"quicksave_1.bin.0","quicksave_1.bin.1"}.All(n=>File.ReadAllBytes(Path.Combine(TargetSaves(),n)).SequenceEqual(checkpoint)),"Both F6 generations copied exactly");
   Require(Directory.GetFiles(TargetSaves()).Length==3&&!Directory.Exists(Path.Combine(target,"UserData","Seeds")),"Unrelated files and randomizer seeds excluded");
   using(var receipt=JsonDocument.Parse(File.ReadAllText(Path.Combine(Path.GetDirectoryName(TargetSaves())!,"redux-story-import.json"))))Require(receipt.RootElement.GetProperty("PreviousContentHash").GetString()==oldHash&&receipt.RootElement.GetProperty("CurrentContentHash").GetString()==newHash,"Import receipt binds exact old and new profiles");
   Refused(()=>ReduxStoryUpgrade.Import(source),"Existing destination saves refused without overwrite");
   Require(before.All(x=>StoryShuffle.HashFile(x.Key)==x.Value),"Previous installation and seed bytes remain unchanged");
   Require(new[]{"quicksave_1.bin.0","quicksave_1.bin.1"}.All(n=>File.ReadAllBytes(Path.Combine(TargetSaves(),n)).SequenceEqual(checkpoint)),"Rejected repeat import leaves current F6 bytes unchanged");
   Settings.OverrideRoot=Path.Combine(scratch,"corrupt-checkpoint-target");Directory.CreateDirectory(ReduxProfileService.DirectoryPath);File.WriteAllBytes(ReduxProfileService.Pack,newPack);
   byte[] corrupt=(byte[])checkpoint.Clone();corrupt[^1]^=1;File.WriteAllBytes(Path.Combine(SourceSaves(),"quicksave_1.bin.0"),corrupt);
   Refused(()=>ReduxStoryUpgrade.Import(source),"Corrupt F6 CRC refused before destination mutation");
   Require(!Directory.Exists(Path.Combine(Settings.User,"ContentProfiles",newHash,"Game","saves")),"Corrupt checkpoint creates no destination saves");
   File.WriteAllBytes(Path.Combine(SourceSaves(),"quicksave_1.bin.0"),checkpoint);File.WriteAllBytes(Path.Combine(SourceSaves(),"earthbound.srm"),phone[..^1]);
   Refused(()=>ReduxStoryUpgrade.Import(source),"Wrong phone size refused before destination mutation");
   File.WriteAllBytes(Path.Combine(SourceSaves(),"earthbound.srm"),phone);
   File.WriteAllText(Path.Combine(ReduxProfileService.DirectoryPath,"profile.json"),JsonSerializer.Serialize(new{contentId=ReduxProfileService.ContentId,assetPackSha256=newHash}));
   Directory.CreateDirectory(Settings.BaseGame);var settings=new Settings();ReduxProfileService.Select(settings);
   Require(Path.GetFileName(Path.GetDirectoryName(Settings.Game))==newHash,"New profile selects its actual save namespace");
   File.WriteAllText(Path.Combine(ReduxProfileService.DirectoryPath,"profile.json"),JsonSerializer.Serialize(new{contentId=ReduxProfileService.ContentId,assetPackSha256=oldHash}));
   Refused(()=>ReduxProfileService.Select(settings),"Mismatched metadata refused even for a compatible legacy hash");
   Require(inputHashes.All(x=>StoryShuffle.HashFile(x.Key)==x.Value),"All supplied pack and owner save inputs unchanged");
   File.WriteAllText(Path.Combine(scratch,"results.json"),JsonSerializer.Serialize(new{Passed=true,OldPackSha256=oldHash,NewPackSha256=newHash,ActualCheckpointSha256=StoryShuffle.Hash(checkpoint),PhoneSha256=StoryShuffle.Hash(phone),Checks=checks,FullPlaythroughVerified=false,Limits=new[]{"Actual launcher import logic on private copies; no natural full story or randomized playthrough claim.","Native cold-load/movement verification is performed separately on the copied checkpoint."}},Settings.JsonOptions));
  } finally {Settings.OverrideRoot=priorOverride;Settings.SessionDirectory=priorSession;}
 }
}
