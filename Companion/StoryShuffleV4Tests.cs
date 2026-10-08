using System.Buffers.Binary;
using System.Text.Json;
namespace EarthBoundCompanion;

static class StoryShuffleV4Tests {
 internal static void Run(string assetPath,string directory) {
  directory=Path.GetFullPath(directory);Directory.CreateDirectory(directory);
  byte[] original=File.ReadAllBytes(assetPath);string hash=StoryShuffle.Hash(original);var policy=ProgressionGuard.CheckBase(original);
  void Require(bool value,string label){if(!value)throw new InvalidDataException(label);}
  var all=new ShuffleOptions {Mode="Surprise"};var sample=StoryShuffle.Build(original,"595173162",all);
  Require(sample.Pack.SequenceEqual(StoryShuffle.Build(original,"595173162",all).Pack),"Nondeterministic v4 seed");
  Require(!sample.Pack.SequenceEqual(StoryShuffle.Build(original,"different",all).Pack),"Seeds are identical");
  var items=StoryShuffleV4.Catalog(original);var (npcStart,npcLength)=StoryShuffle.Range(original,StoryShuffle.Npcs);var (shopStart,shopLength)=StoryShuffle.Range(original,StoryShuffle.Shops);var (enemyStart,enemyLength)=StoryShuffle.Range(original,StoryShuffle.Enemies);
  int mixedGifts=0,moneyGifts=0,cookieDrops=0,firstSlots=0;
  for(int i=0;i<npcLength/17;i++)if(original[npcStart+i*17]==2) {
   int p=npcStart+i*17;uint before=BinaryPrimitives.ReadUInt32LittleEndian(original.AsSpan(p+13)),after=BinaryPrimitives.ReadUInt32LittleEndian(sample.Pack.AsSpan(p+13));
   if(before>=256&&after<254)moneyGifts++;
   if(before>0&&before<254&&after>0&&after<254&&items[before].Kind!=items[after].Kind)mixedGifts++;
  }
  for(int i=0;i<shopLength;i+=7)if(original[shopStart+i]!=sample.Pack[shopStart+i])firstSlots++;
  for(int i=1;i<231;i++)if(original[enemyStart+i*94+88]==88&&sample.Pack[enemyStart+i*94+88]!=88)cookieDrops++;
  Require(mixedGifts>50&&moneyGifts>0&&cookieDrops>0&&firstSlots>0,"Ordinary loot is still overprotected");
  Require(sample.Counts.GetValueOrDefault("Wild encounters")>100,"Wild encounter changes missing");
  // Directly assert known trade IDs and story key categories independently of
  // the generator's eligibility predicate; script grants are byte-immutable.
  int[] tradeIds=[90,92,93,95,108,127,140,190,224];
  for(int seed=0;seed<1000;seed++) {
   var options=all with {Mode=seed%2==0?"Balanced":"Surprise"};var built=StoryShuffle.Build(original,"v4-"+seed,options);
   StoryShuffleV4.Validate(original,built.Pack,options);
   for(int i=0;i<shopLength;i++)if(tradeIds.Contains(original[shopStart+i])||items[original[shopStart+i]].Kind is >=0x38 and <=0x3B)
    Require(original[shopStart+i]==built.Pack[shopStart+i],"Required stock removed");
   for(int i=0;i<npcLength/17;i++)if(original[npcStart+i*17]==2) {
    int p=npcStart+i*17;uint before=BinaryPrimitives.ReadUInt32LittleEndian(original.AsSpan(p+13)),after=BinaryPrimitives.ReadUInt32LittleEndian(built.Pack.AsSpan(p+13));
    if(before<254&&(items[before].Kind is >=0x38 and <=0x3B||before is 1 or 95 or 105 or 139 or 166 or 184))Require(before==after,"Story gift or pizza supply removed");
    if(before!=after)Require(after>0&&after<254&&items[after].Kind is not (>=0x38 and <=0x3B)&&after is not (1 or 105 or 139 or 166 or 184 or 27),"Key or Casey bat introduced as random loot");
   }
   foreach(string name in new[]{StoryShuffle.Items,StoryShuffleV4.Groups,StoryShuffleV4.BattlePointers,StoryShuffleV4.PlacementPointers,"US/events/bank_c3_scripts_combined.bin"})
    Require(StoryShuffle.Table(original,name).SequenceEqual(StoryShuffle.Table(built.Pack,name)),"Immutable story/battle asset changed: "+name);
   for(int i=1;i<231;i++) {
    int p=enemyStart+i*94;
    Require(original[p+89]==built.Pack[p+89],"Drop chance changed");
    if(original[p+86]!=0)Require(original.AsSpan(p,94).SequenceEqual(built.Pack.AsSpan(p,94)),"Boss record changed");
   }
   int ext=231*94;Require(original.AsSpan(enemyStart+ext,enemyLength-ext).SequenceEqual(built.Pack.AsSpan(enemyStart+ext,enemyLength-ext)),"Redux AI extension changed");
  }
  for(int flags=1;flags<32;flags++)foreach(string mode in new[]{"Balanced","Surprise"}) {
   var options=new ShuffleOptions {Mode=mode,Gifts=(flags&1)!=0,Shops=(flags&2)!=0,EnemyStats=(flags&4)!=0,EnemyDrops=(flags&8)!=0,EnemyEncounters=(flags&16)!=0};
   var built=StoryShuffle.Build(original,"options",options);StoryShuffleV4.Validate(original,built.Pack,options);
   foreach(var (enabled,name) in new[]{(options.Gifts,StoryShuffle.Npcs),(options.Shops,StoryShuffle.Shops),(options.EnemyStats||options.EnemyDrops,StoryShuffle.Enemies),(options.EnemyEncounters,StoryShuffleV4.Placements)})
    if(!enabled)Require(StoryShuffle.Table(original,name).SequenceEqual(StoryShuffle.Table(built.Pack,name)),"Disabled option changed "+name);
  }
  int rejected=0;
  void Reject(byte[] bad,string label,ShuffleOptions? opts=null) {try{StoryShuffleV4.Validate(original,bad,opts??all);}catch(InvalidDataException){rejected++;return;}throw new InvalidDataException("Corruption accepted: "+label);}
  void Flip(int at,string label){var bad=(byte[])sample.Pack.Clone();bad[at]^=1;Reject(bad,label);}
  Flip(shopStart+Enumerable.Range(0,shopLength).First(i=>original[shopStart+i]==90),"Monkey Cave hamburger stock");
  int pizza=Enumerable.Range(0,npcLength/17).First(i=>original[npcStart+i*17]==2&&BinaryPrimitives.ReadUInt32LittleEndian(original.AsSpan(npcStart+i*17+13))==95);
  Flip(npcStart+pizza*17+13,"Pizza supply");
  Flip(StoryShuffle.Range(original,StoryShuffleV4.BattlePointers).Start,"Scripted lineup pointer");
  Flip(StoryShuffle.Range(original,StoryShuffleV4.Groups).Start,"Battle lineup data");
  Flip(StoryShuffle.Range(original,StoryShuffleV4.PlacementPointers).Start,"Placement pointer");
  var slot=StoryShuffleV4.PlacementSlots(original)[0];var badEncounter=(byte[])sample.Pack.Clone();BinaryPrimitives.WriteUInt16LittleEndian(badEncounter.AsSpan(StoryShuffle.Range(original,StoryShuffleV4.Placements).Start+slot.Offset),65535);Reject(badEncounter,"Out-of-range encounter");
  Flip(StoryShuffle.Range(original,StoryShuffleV4.Placements).Start+slot.Offset-1,"Spawn weight");
  Flip(enemyStart+55*94+89,"Drop chance");Flip(enemyStart+55*94+69,"Enemy AI");Flip(original.Length-1,"Other asset");
  Reject(sample.Pack,"Disabled gifts",all with {Gifts=false});Reject(sample.Pack,"Disabled encounters",all with {EnemyEncounters=false});
  Settings.OverrideRoot=Path.Combine(directory,"isolated-library");
  try {
   Directory.CreateDirectory(Settings.BaseGame);File.WriteAllBytes(Path.Combine(Settings.BaseGame,"assets.pak"),original);
   var current=StoryShuffle.Generate("595173162",all);StoryShuffle.Verify(current);
   File.WriteAllText(Path.Combine(current.Session,"saves","sentinel.txt"),"preserve");
   Require(File.ReadAllText(Path.Combine(StoryShuffle.Generate("595173162",all).Session,"saves","sentinel.txt"))=="preserve","Regeneration overwrote saves");
   var legacy=StoryShuffle.Generate("595173162",all,version:3);StoryShuffle.Verify(legacy);
   Require(legacy.Id!=current.Id&&legacy.Version==3,"Legacy/current seed isolation failed");
   if(hash=="d9a772d10aff68bdf93c077cda640d42b835884d6834bb18bf0d43c3800f57bb") {
    Require(legacy.Id=="04f0667f8781f08a89090d0d775b4564e14ee6f0e21856ea9ecd515a2084fd8f"&&legacy.PackHash=="bf52a5c7647fdd6426e334097a1ec073c2e830e7e127894de9082a06578824b3","Known owner v3 fixture changed");
   }
   Require(File.ReadAllBytes(legacy.Pak).SequenceEqual(StoryShuffle.BuildV3(original,"595173162",all).Pack),"V3 algorithm changed");
   Require(StoryShuffle.ImportRecipe(Path.Combine(legacy.Folder,"recipe.ebseed.json")).Version==3,"V3 import rejected");
   Require(StoryShuffle.ImportRecipe(Path.Combine(current.Folder,"recipe.ebseed.json")).Version==4,"V4 import rejected");
   File.WriteAllText(Path.Combine(directory,"native-seed-path.txt"),current.Pak);
   File.WriteAllText(Path.Combine(directory,"legacy-seed-path.txt"),legacy.Pak);
  }finally{Settings.OverrideRoot=null;Settings.SessionDirectory=null;}
  Require(StoryShuffle.HashFile(assetPath)==hash,"Owner pack changed");
  File.WriteAllText(Path.Combine(directory,"results.json"),JsonSerializer.Serialize(new {Passed=true,Version=4,policy.ContentId,BaseHash=hash,Seeds=1000,OptionCombinations=62,RejectedCorruptions=rejected,Sample=sample.Counts,CrossCategoryGifts=mixedGifts,MoneyGifts=moneyGifts,ChangedCookieDrops=cookieDrops,ChangedFirstShopSlots=firstSlots,FullPlaythroughVerified=false},Settings.JsonOptions));
 }
}
