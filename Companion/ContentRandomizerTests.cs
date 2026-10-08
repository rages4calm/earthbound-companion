using System.Buffers.Binary;
using System.Text.Json;
namespace EarthBoundCompanion;

static class ContentRandomizerTests {
 internal static void Run(string assetPath,string directory) {
  assetPath=Path.GetFullPath(assetPath);directory=Path.GetFullPath(directory);Directory.CreateDirectory(directory);
  byte[] original=File.ReadAllBytes(assetPath);var policy=ProgressionGuard.CheckBase(original);
  string originalHash=StoryShuffle.Hash(original);var all=new ShuffleOptions();var checks=new List<string>();
  void Require(bool condition,string label){if(!condition)throw new InvalidDataException(label);}
  var reference=StoryShuffle.BuildV3(original,"Redux-reference",all);
  Require(reference.Pack.SequenceEqual(StoryShuffle.BuildV3(original,"Redux-reference",all).Pack),"Content seed is not deterministic");
  Require(!reference.Pack.SequenceEqual(StoryShuffle.BuildV3(original,"Redux-other",all).Pack),"Different content seeds are identical");
  checks.Add("Deterministic seeds and distinct seed output");
  var (enemyStart,enemyLength)=StoryShuffle.Range(original,StoryShuffle.Enemies);
  int extensionStart=enemyStart+StoryShuffle.EnemyRecordCount*94;
  int extensionLength=enemyLength-StoryShuffle.EnemyRecordCount*94;
  var (shopStart,shopLength)=StoryShuffle.Range(original,StoryShuffle.Shops);
  var (npcStart,npcLength)=StoryShuffle.Range(original,StoryShuffle.Npcs);
  for(int seed=0;seed<1000;seed++) {
   var options=all with {Mode=seed%2==0?"Balanced":"Surprise"};var built=StoryShuffle.BuildV3(original,"content-"+seed,options);
   ProgressionGuard.Validate(original,built.Pack,options);
   Require(original.AsSpan(extensionStart,extensionLength).SequenceEqual(built.Pack.AsSpan(extensionStart,extensionLength)),"Enemy-AI extension changed");
   foreach(int enemy in policy.Enemies)Require(original.AsSpan(enemyStart+enemy*94,94).SequenceEqual(built.Pack.AsSpan(enemyStart+enemy*94,94)),"Protected scripted enemy changed");
   for(int offset=0;offset<shopLength;offset++)if(offset%7==0||policy.Items.Contains(original[shopStart+offset]))
    Require(original[shopStart+offset]==built.Pack[shopStart+offset],"Baseline stock or protected item source changed");
   for(int offset=0;offset<npcLength;offset+=17) {
    uint item=BinaryPrimitives.ReadUInt32LittleEndian(original.AsSpan(npcStart+offset+13));
    if(original[npcStart+offset]!=2||item>=254||policy.Items.Contains((int)item))
     Require(original.AsSpan(npcStart+offset,17).SequenceEqual(built.Pack.AsSpan(npcStart+offset,17)),"Quest or protected gift changed");
   }
  }
  checks.Add("1000 seeds across Balanced and Surprise preserve protected gift/shop sources, scripted enemies and enemy-AI data");
  for(int flags=1;flags<16;flags++)foreach(string mode in new[]{"Balanced","Surprise"}) {
   var options=new ShuffleOptions {Mode=mode,Gifts=(flags&1)!=0,Shops=(flags&2)!=0,EnemyStats=(flags&4)!=0,EnemyDrops=(flags&8)!=0};
   var built=StoryShuffle.BuildV3(original,"content-options",options);ProgressionGuard.Validate(original,built.Pack,options);
  }
  checks.Add("All 30 option/preset combinations pass the content policy");
  void Rejected(byte[] bad,string label){bool refused=false;try{ProgressionGuard.Validate(original,bad,all);}catch(InvalidDataException){refused=true;}Require(refused,label);}
  if(extensionLength>0) {
   byte[] bad=(byte[])reference.Pack.Clone();bad[extensionStart+12]^=1;Rejected(bad,"Modified enemy-AI pointer accepted");
   bad=(byte[])reference.Pack.Clone();bad[extensionStart+8]^=1;Rejected(bad,"Malformed enemy-AI count accepted");
  }
  byte[] badProtected=(byte[])reference.Pack.Clone();int protectedShop=Enumerable.Range(0,shopLength).First(i=>policy.Items.Contains(original[shopStart+i]));
  badProtected[shopStart+protectedShop]=0;Rejected(badProtected,"Removed protected stock accepted");
  byte[] badScript=(byte[])reference.Pack.Clone();badScript[^1]^=1;Rejected(badScript,"Modified story assets accepted");
  checks.Add("Independent corruption checks reject altered AI pointers/counts, protected stock and story assets");
  Settings.OverrideRoot=Path.Combine(directory,"isolated-library");
  try {
   Directory.CreateDirectory(Settings.BaseGame);File.WriteAllBytes(Path.Combine(Settings.BaseGame,"assets.pak"),original);
   var seed=StoryShuffle.Generate("Redux-reference",all,version:3);StoryShuffle.Verify(seed);
   Require(seed.ContentId==policy.ContentId&&seed.ContentName==policy.DisplayName,"Seed has the wrong content profile");
   File.WriteAllText(Path.Combine(seed.Session,"saves","sentinel.txt"),"preserve content save");
   var repeated=StoryShuffle.Generate("Redux-reference",all,version:3);
   Require(File.ReadAllText(Path.Combine(repeated.Session,"saves","sentinel.txt"))=="preserve content save","Regeneration overwrote content saves");
   var recipe=StoryShuffle.ImportRecipe(Path.Combine(seed.Folder,"recipe.ebseed.json"));
   Require(recipe.ContentId==policy.ContentId&&recipe.BaseHash==originalHash,"Recipe lost content identity");
   File.WriteAllText(Path.Combine(directory,"native-seed-path.txt"),seed.Pak);
   checks.Add("Content-specific generation, verification, recipes and separate saves survive regeneration");
  } finally {Settings.OverrideRoot=null;Settings.SessionDirectory=null;}
  Require(StoryShuffle.Hash(original)==originalHash&&StoryShuffle.HashFile(assetPath)==originalHash,"Original content pack mutated");
  File.WriteAllText(Path.Combine(directory,"results.json"),JsonSerializer.Serialize(new {
   policy.ContentId,policy.DisplayName,BaseHash=originalHash,Seeds=1000,OptionCombinations=30,
   ProtectedItems=policy.Items.Count,ProtectedEnemies=policy.Enemies.Count,ShopRows=shopLength/7,
   EnemyRecords=StoryShuffle.EnemyRecordCount,EnemyAiBytes=extensionLength,Passed=true,Checks=checks,
   FullPlaythroughVerified=false
  },Settings.JsonOptions));
 }
}
