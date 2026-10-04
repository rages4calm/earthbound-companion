using System.Buffers.Binary;
using System.Text.Json;
namespace EarthBoundCompanion;

static class RandomizerTests {
 public static void Run(string directory) {
  directory=Path.GetFullPath(directory);Directory.CreateDirectory(directory);
  byte[] original=File.ReadAllBytes(Path.Combine(Settings.BaseGame,"assets.pak"));string baseHash=StoryShuffle.Hash(original);
  var report=new List<string>();
  void Require(bool condition,string label){if(!condition)throw new Exception(label);}
  var all=new ShuffleOptions();var one=StoryShuffle.Build(original,"Ness-2026",all);
  Require(one.Pack.SequenceEqual(StoryShuffle.Build(original,"Ness-2026",all).Pack),"Same seed not deterministic");
  Require(!one.Pack.SequenceEqual(StoryShuffle.Build(original,"Paula-2026",all).Pack),"Different seed did not change result");
  Require(!one.Pack.SequenceEqual(StoryShuffle.Build(original,"Ness-2026",all with {Mode="Surprise"}).Pack),"Modes did not change result");
  Require(StoryShuffle.Hash(original)==baseHash,"Base asset data mutated");
  report.Add("PASS: deterministic output, distinct seeds and presets, base data unchanged");
  var itemTable=StoryShuffle.Table(original,StoryShuffle.Items).ToArray();
  bool Optional(int id)=>id>0&&id<254&&!ProgressionGuard.Items.Contains(id)&&BinaryPrimitives.ReadUInt16LittleEndian(itemTable.AsSpan(id*39+26))>0&&itemTable[id*39+25] is 0x10 or 0x11 or 0x14 or 0x18 or 0x1C or 0x20 or 0x24 or 0x28 or 0x2C or 0x30;
  // Known Monkey Cave requests and the early Cracked bat must be protected
  // independently of whatever the generated policy currently classifies.
  foreach(int id in new[]{0x11,0x5A,0x5D,0x5F,0x7F,0x8C,0xA6,0xB8,0xBE,0xE0})Require(ProgressionGuard.Items.Contains(id),"Missing known story/trade protection: "+id);
  for(int seed=0;seed<1000;seed++) {
   var options=all with {Mode=seed%2==0?"Balanced":"Surprise"};var built=StoryShuffle.Build(original,seed.ToString(),options);
   var allowed=new HashSet<int>();
   var (npcStart,npcLength)=StoryShuffle.Range(original,StoryShuffle.Npcs);
   for(int i=0;i<npcLength/17;i++) {
    int p=npcStart+i*17;uint old=BinaryPrimitives.ReadUInt32LittleEndian(original.AsSpan(p+13));
    if(original[p]==2&&old<254&&Optional((int)old)) {
     uint next=BinaryPrimitives.ReadUInt32LittleEndian(built.Pack.AsSpan(p+13));Require(next<254&&Optional((int)next),"Gift gained invalid or story item");
     Require(itemTable[(int)old*39+25]==itemTable[(int)next*39+25],"Gift category changed");
     for(int k=13;k<17;k++)allowed.Add(p+k);
    }
   }
   var (shopStart,shopLength)=StoryShuffle.Range(original,StoryShuffle.Shops);
   for(int i=0;i<shopLength;i++) {
    int p=shopStart+i;if(i%7!=0&&Optional(original[p])) {
     Require(Optional(built.Pack[p]),"Shop gained invalid or story item");
     Require(itemTable[original[p]*39+25]==itemTable[built.Pack[p]*39+25],"Shop item category changed");allowed.Add(p);
    }
   }
   var (enemyStart,enemyLength)=StoryShuffle.Range(original,StoryShuffle.Enemies);
   for(int i=1;i<enemyLength/94;i++) {
    int p=enemyStart+i*94;
    if(ProgressionGuard.Enemies.Contains(i)||original[p+86]!=0||original[p+54]==0)continue;
    foreach(int offset in new[]{33,56,58}) {
     int before=BinaryPrimitives.ReadUInt16LittleEndian(original.AsSpan(p+offset)),after=BinaryPrimitives.ReadUInt16LittleEndian(built.Pack.AsSpan(p+offset));
     int low=(before*(options.Mode=="Balanced"?85:70)+50)/100,high=(before*(options.Mode=="Balanced"?115:130)+50)/100;
     Require(after>=Math.Max(before>0?1:0,low)&&after<=Math.Max(before>0?1:0,high),"Enemy stat out of bounds");allowed.Add(p+offset);allowed.Add(p+offset+1);
     if(offset!=33&&before<=255)Require(after<=255,"Enemy offense/defense would wrap in native battle initialization");
    }
    allowed.Add(p+60);
    if(Optional(original[p+88])){Require(Optional(built.Pack[p+88]),"Enemy drop became invalid or story item");allowed.Add(p+88);}
   }
   for(int i=0;i<original.Length;i++)if(original[i]!=built.Pack[i])Require(allowed.Contains(i),"Unexpected mutation at byte "+i);
  }
  report.Add($"PASS: 1000 seeds across both modes; all original sources of {ProgressionGuard.Items.Count} protected items, {ProgressionGuard.Enemies.Count} scripted-battle enemies, quests, bosses, scripts, maps, prices and rewards unchanged");
  for(int flags=1;flags<16;flags++)foreach(string mode in new[]{"Balanced","Surprise"}) {
   var options=new ShuffleOptions {Mode=mode,Gifts=(flags&1)!=0,Shops=(flags&2)!=0,EnemyStats=(flags&4)!=0,EnemyDrops=(flags&8)!=0};
   var built=StoryShuffle.Build(original,"option-matrix",options);ProgressionGuard.Validate(original,built.Pack,options);
  }
  report.Add("PASS: all 30 valid option/preset combinations pass progression preservation checks");
  // Check the validator itself with changes outside the generator's paths.
  void Rejected(byte[] bad,string label) {bool rejected=false;try{ProgressionGuard.Validate(original,bad,all);}catch(InvalidDataException){rejected=true;}Require(rejected,label);}
  byte[] badSource=(byte[])one.Pack.Clone();var (shopsStart,shopsLength)=StoryShuffle.Range(original,StoryShuffle.Shops);
  int trade=Enumerable.Range(0,shopsLength).First(i=>original[shopsStart+i]==0xE0);badSource[shopsStart+trade]=0x5B;Rejected(badSource,"Missing trade food accepted");
  byte[] badScript=(byte[])one.Pack.Clone();badScript[^1]^=1;Rejected(badScript,"Protected asset mutation accepted");
  byte[] badEnemy=(byte[])one.Pack.Clone();var (enemiesStart,_)=StoryShuffle.Range(original,StoryShuffle.Enemies);badEnemy[enemiesStart+ProgressionGuard.Enemies.First(i=>i>0)*94+33]^=1;Rejected(badEnemy,"Scripted battle mutation accepted");
  byte[] badBase=(byte[])original.Clone();badBase[^1]^=1;bool baseRejected=false;try{StoryShuffle.Build(badBase,"modified-base",all);}catch(InvalidDataException){baseRejected=true;}Require(baseRejected,"Unaudited original accepted");
  report.Add("PASS: guard independently rejects missing trade sources, altered scripts/assets, altered scripted battles and unaudited base data");
  foreach(var table in new[]{StoryShuffle.Npcs,StoryShuffle.Shops,StoryShuffle.Enemies}) {
   var options=new ShuffleOptions {Gifts=table==StoryShuffle.Npcs,Shops=table==StoryShuffle.Shops,EnemyStats=table==StoryShuffle.Enemies,EnemyDrops=false};
   var built=StoryShuffle.Build(original,"isolated-options",options);
   foreach(var unchanged in new[]{StoryShuffle.Npcs,StoryShuffle.Shops,StoryShuffle.Enemies}.Where(n=>n!=table))Require(StoryShuffle.Table(original,unchanged).SequenceEqual(StoryShuffle.Table(built.Pack,unchanged)),"Disabled table mutated");
  }
  report.Add("PASS: independent options leave disabled tables untouched");
  foreach(byte[] broken in new[]{original[..40],original[..(original.Length/2)]}) {
   bool rejected=false;try{StoryShuffle.Build(broken,"bad",all);}catch(InvalidDataException){rejected=true;}Require(rejected,"Malformed pack accepted");
  }
  string actualRoot=Settings.Root;Settings.OverrideRoot=Path.Combine(directory,"library-fixture-v2");
  try {
   Directory.CreateDirectory(Settings.BaseGame);File.WriteAllBytes(Path.Combine(Settings.BaseGame,"assets.pak"),original);
   var seed=StoryShuffle.Generate("Ness-2026",all);StoryShuffle.Verify(seed);
   var alt=StoryShuffle.Generate("Paula-2026",all);Require(seed.Session!=alt.Session,"Seeds share a save directory");
   File.WriteAllText(Path.Combine(seed.Session,"saves","sentinel.txt"),"preserve seed save");
   var repeat=StoryShuffle.Generate("Ness-2026",all);Require(File.ReadAllText(Path.Combine(repeat.Session,"saves","sentinel.txt"))=="preserve seed save","Regeneration overwrote saves");
   Require(StoryShuffle.List().Count(s=>s.Version==StoryShuffle.Version)==2,"Seed library failed");
   var recipe=StoryShuffle.ImportRecipe(Path.Combine(seed.Folder,"recipe.ebseed.json"));Require(recipe.Seed==seed.Seed&&recipe.Options==all,"Seed recipe roundtrip failed");
   var wrongRecipe=Path.Combine(directory,"bad.ebseed.json");File.WriteAllText(wrongRecipe,"{\"Generator\":\"earthbound.app\",\"Version\":1,\"Seed\":\"10\",\"Options\":{},\"BaseHash\":\"bad\"}");
   bool rejected=false;try{StoryShuffle.ImportRecipe(wrongRecipe);}catch(InvalidDataException){rejected=true;}Require(rejected,"Website file accepted as native recipe");
   rejected=false;try{StoryShuffle.Generate("wrong-base",all,new string('0',64));}catch(InvalidDataException){rejected=true;}Require(rejected,"Different base accepted");
   var settings=new Settings();Settings.SessionDirectory=seed.Session;settings.Save();
   Require(File.ReadAllText(Path.Combine(seed.Session,"earthbound.ini")).Contains(Path.Combine(Settings.Root,"msu")),"MSU path not absolute in seed session");
   string backup=Settings.Backup(true);using(var zip=System.IO.Compression.ZipFile.OpenRead(backup))Require(zip.GetEntry("saves/sentinel.txt")!=null,"Seed saves not backed up");
   // Recovery uses temporary seed sessions, never the installed user's saves.
   string engine=Path.Combine(Settings.BaseGame,"earthbound.exe");File.WriteAllText(engine,"fixture-engine-1");
   string phonePath=Path.Combine(seed.Session,"saves","earthbound.srm");byte[] phone=new byte[8192];phone[10]=123;File.WriteAllBytes(phonePath,phone);
   string quickPath=Path.Combine(seed.Session,"saves","quicksave_5.bin.0");byte[] quick=new byte[24];"EBSD"u8.CopyTo(quick);BinaryPrimitives.WriteUInt16LittleEndian(quick.AsSpan(4),(ushort)ProgressionGuard.SaveStateVersion);quick[20]=123;BinaryPrimitives.WriteUInt32LittleEndian(quick.AsSpan(16),4);BinaryPrimitives.WriteUInt32LittleEndian(quick.AsSpan(12),SaveRecovery.Crc(quick.AsSpan(20)));File.WriteAllBytes(quickPath,quick);
   string recovery=Settings.Backup(true,seed.Session);File.WriteAllBytes(phonePath,new byte[8192]);File.WriteAllBytes(quickPath,[5,6,7]);
   var restored=SaveRecovery.Restore(recovery,seed.Session,true);Require(restored.Files==1&&File.ReadAllBytes(phonePath).SequenceEqual(phone)&&File.ReadAllBytes(quickPath).SequenceEqual(new byte[]{5,6,7})&&File.Exists(restored.PreviousBackup),"Phone-only restore or prior backup failed");
   restored=SaveRecovery.Restore(recovery,seed.Session,false);Require(restored.Files>=2&&File.ReadAllBytes(quickPath).SequenceEqual(quick),"Full restore failed");
   bool Refused(string zipPath,string destination,bool phoneOnly) {try{SaveRecovery.Restore(zipPath,destination,phoneOnly);return false;}catch(InvalidDataException){return true;}}
   Require(Refused(recovery,alt.Session,true),"Cross-seed restore accepted");
   File.WriteAllText(engine,"fixture-engine-2");Require(Refused(recovery,seed.Session,false),"Incompatible quick save accepted");Require(SaveRecovery.Restore(recovery,seed.Session,true).Files==1,"Portable phone save refused");
   string BrokenBackup(string name,bool traversal) {
    string dest=Path.Combine(directory,name);using var source=System.IO.Compression.ZipFile.OpenRead(recovery);using var target=new System.IO.Compression.ZipArchive(File.Open(dest,FileMode.Create),System.IO.Compression.ZipArchiveMode.Create);
    foreach(var entry in source.Entries){using var writer=target.CreateEntry(entry.FullName).Open();if(entry.FullName=="saves/earthbound.srm"&&!traversal)writer.Write(new byte[8192]);else{using var reader=entry.Open();reader.CopyTo(writer);}}
    if(traversal){using var writer=new StreamWriter(target.CreateEntry("saves/../../escape.txt").Open());writer.Write("must refuse");}return dest;
   }
   string tamper=BrokenBackup("restore-tamper.zip",false),traversal=BrokenBackup("restore-traversal.zip",true);var unchangedPhone=File.ReadAllBytes(phonePath);
   Require(Refused(tamper,seed.Session,true)&&Refused(traversal,seed.Session,true)&&File.ReadAllBytes(phonePath).SequenceEqual(unchangedPhone),"Invalid backup changed destination");
   report.Add("PASS: phone-only/full restore, backup before restore, cross-seed refusal, engine-build protection, portable phone saves, damaged backup and path traversal rejection");
   Settings.SessionDirectory=null;settings.Save();Require(!File.Exists(Path.Combine(Settings.BaseGame,"saves","sentinel.txt")),"Seed save leaked into story");
   File.WriteAllText(Path.Combine(directory,"native-seed-path.txt"),seed.Pak);
   File.WriteAllText(Path.Combine(directory,"native-session-path.txt"),seed.Session);
   File.WriteAllText(Path.Combine(directory,"counts.json"),JsonSerializer.Serialize(seed.Changes,Settings.JsonOptions));
   // Tampered seed refuses play and regeneration; preserve its original pack after the rejection check.
   byte[] valid=File.ReadAllBytes(alt.Pak),tampered=(byte[])valid.Clone();tampered[^1]^=1;File.WriteAllBytes(alt.Pak,tampered);
   rejected=false;try{StoryShuffle.Verify(alt);}catch(InvalidDataException){rejected=true;}Require(rejected,"Tampered seed accepted");File.WriteAllBytes(alt.Pak,valid);
   string legacyId=StoryShuffle.Hash(System.Text.Encoding.UTF8.GetBytes($"{StoryShuffle.Name}\n1\nlegacy-safety-test\n{JsonSerializer.Serialize(all)}\n{baseHash}"));
   string legacyFolder=Path.Combine(StoryShuffle.Library,legacyId);Directory.CreateDirectory(legacyFolder);
   var legacy=new SeedRecord {Seed="legacy-safety-test",Version=1,Options=all,Id=legacyId,BaseHash=baseHash,PackHash=StoryShuffle.Hash(badSource),Folder=legacyFolder};
   File.WriteAllText(Path.Combine(legacyFolder,"seed.json"),JsonSerializer.Serialize(legacy));File.WriteAllBytes(legacy.Pak,badSource);Directory.CreateDirectory(Path.Combine(legacy.Session,"saves"));File.WriteAllText(Path.Combine(legacy.Session,"saves","sentinel.txt"),"legacy save");
   legacy=StoryShuffle.Read(legacyFolder);rejected=false;try{StoryShuffle.Verify(legacy);}catch(InvalidDataException){rejected=true;}
   Require(rejected&&File.ReadAllText(Path.Combine(legacy.Session,"saves","sentinel.txt"))=="legacy save","Unsafe version 1 seed played or its saves were lost");
   report.Add("PASS: unsafe version 1 seed remains recoverable but cannot launch even with a valid manifest checksum");
  }finally{Settings.OverrideRoot=null;Settings.SessionDirectory=null;}
  report.Add("PASS: atomic library records, recipe roundtrip, separate save directories, preserved saves on regeneration, seed backups, base mismatch and tamper rejection");
  Require(StoryShuffle.HashFile(Path.Combine(actualRoot,"Game","assets.pak"))==baseHash,"Installed base pack changed");
  report.Add("Base SHA256: "+baseHash);report.Add("Seed Ness-2026 SHA256: "+StoryShuffle.Hash(one.Pack));
  File.WriteAllLines(Path.Combine(directory,"tests.txt"),report);
 }
}
