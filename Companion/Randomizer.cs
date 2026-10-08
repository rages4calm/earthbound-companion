using System.Buffers.Binary;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace EarthBoundCompanion;

public sealed record ShuffleOptions {
 public string Mode { get; init; } = "Balanced";
 public bool Gifts { get; init; } = true;
 public bool Shops { get; init; } = true;
 public bool EnemyStats { get; init; } = true;
 public bool EnemyDrops { get; init; } = true;
 public bool EnemyEncounters { get; init; } = true;
 public void Validate() {
  if(Mode is not ("Balanced" or "Surprise"))throw new InvalidDataException("Choose Balanced or Surprise Story Shuffle.");
  if(!Gifts&&!Shops&&!EnemyStats&&!EnemyDrops&&!EnemyEncounters)throw new InvalidDataException("Enable at least one shuffle option.");
 }
}
public sealed class SeedRecord {
 public string Generator { get; set; } = StoryShuffle.Name;
 public int Version { get; set; } = StoryShuffle.Version;
 public string Seed { get; set; } = "";
 public ShuffleOptions Options { get; set; } = new();
 public string Id { get; set; } = "";
 public string ContentId { get; set; } = "earthbound-usa";
 public string ContentName { get; set; } = "EarthBound (USA)";
 public string BaseHash { get; set; } = "";
 public string PackHash { get; set; } = "";
 public DateTime CreatedUtc { get; set; }
 public Dictionary<string,int> Changes { get; set; } = [];
 [JsonIgnore] public string Folder { get; set; } = "";
 [JsonIgnore] public string Pak => Path.Combine(Folder,"assets.pak");
 [JsonIgnore] public string Session => Path.Combine(Folder,"Game");
 public override string ToString() => $"{Seed} · {ContentName} · {Options.Mode} · v{Version}"+(Version<StoryShuffle.Version?" · legacy safety review":"");
}
public sealed record SeedRecipe(string Generator,int Version,string Seed,ShuffleOptions Options,string BaseHash,string ContentId="earthbound-usa",string ContentName="EarthBound (USA)");
public sealed record ShuffleChange(string Table, int Entry, string Before, string After);
internal sealed record ShuffleLayout(string Header, Dictionary<string,int> Assets);
internal sealed record ShuffleBuild(byte[] Pack, List<ShuffleChange> Spoiler, Dictionary<string,int> Counts);

static class StoryShuffle {
 public const string Name = "EarthBound Companion Story Shuffle";
 public const int Version = 4;
  internal const string Npcs="data/npc_config_table.bin",Items="data/item_configuration_table.bin",Shops="data/store_table.bin",Enemies="data/enemy_configuration_table.bin";
  internal const int EnemyRecordCount=231;
 public static string Library => Path.Combine(Settings.User,"Seeds");
 static readonly ShuffleLayout Layout = LoadLayout();
 static ShuffleLayout LoadLayout() {
  using var stream=typeof(StoryShuffle).Assembly.GetManifestResourceStream("EarthBoundCompanion.randomizer-layout.json")
   ??typeof(StoryShuffle).Assembly.GetManifestResourceNames().Where(n=>n.EndsWith("randomizer-layout.json")).Select(n=>typeof(StoryShuffle).Assembly.GetManifestResourceStream(n)).FirstOrDefault()
   ??throw new InvalidDataException("Native randomizer asset registry is missing.");
  return JsonSerializer.Deserialize<ShuffleLayout>(stream)??throw new InvalidDataException("Native randomizer registry is empty.");
 }
 public static string Hash(byte[] data)=>Convert.ToHexString(SHA256.HashData(data)).ToLowerInvariant();
 public static string HashFile(string path){using var stream=File.OpenRead(path);return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();}
 public static string CleanSeed(string seed) {
  seed=seed.Trim();if(seed.Length is <1 or >80||seed.Any(char.IsControl))throw new InvalidDataException("Use a seed of 1–80 characters without control characters.");
  return seed;
 }
 static string Identity(string seed,ShuffleOptions options,string baseHash,string contentId,int version=Version) {
  string serialized=version<4?JsonSerializer.Serialize(new {options.Mode,options.Gifts,options.Shops,options.EnemyStats,options.EnemyDrops}):JsonSerializer.Serialize(options);
  string identity=version<3?$"{Name}\n{version}\n{seed}\n{serialized}\n{baseHash}":$"{Name}\n{version}\n{contentId}\n{seed}\n{serialized}\n{baseHash}";
  return Hash(Encoding.UTF8.GetBytes(identity));
 }
 static string ActiveBasePack()=>Settings.Load().Pak;
 public static IReadOnlyList<SeedRecord> List() {
  if(!Directory.Exists(Library))return [];
  var result=new List<SeedRecord>();
  foreach(var folder in Directory.EnumerateDirectories(Library)) {
   try {var seed=Read(folder);result.Add(seed);}catch(Exception e)when(e is IOException or JsonException or InvalidDataException or ArgumentException) { /* Incomplete or unknown builds remain on disk for recovery. */ }
  }
  return result.OrderByDescending(s=>s.CreatedUtc).ToArray();
 }
 public static SeedRecord Read(string folder) {
  var record=JsonSerializer.Deserialize<SeedRecord>(File.ReadAllText(Path.Combine(folder,"seed.json")))??throw new InvalidDataException("Missing seed manifest.");
  if(record.Options==null)throw new InvalidDataException("Missing seed options.");
  if(record.Version<4)record.Options=record.Options with {EnemyEncounters=false};
  CheckRecipe(new(record.Generator,record.Version,record.Seed,record.Options,record.BaseHash,record.ContentId,record.ContentName),true);
  if(record.PackHash==null||record.PackHash.Length!=64||!record.PackHash.All(Uri.IsHexDigit)||record.Changes==null)
   throw new InvalidDataException("Invalid seed manifest.");
  if(record.Id!=Identity(record.Seed,record.Options,record.BaseHash,record.ContentId,record.Version)||Path.GetFileName(folder)!=record.Id)
   throw new InvalidDataException("Seed identity does not match its manifest.");
  record.Folder=Path.GetFullPath(folder);return record;
 }
 public static void Verify(SeedRecord seed) {
  var fresh=Read(seed.Folder);
  if(fresh.Id!=seed.Id||fresh.PackHash!=seed.PackHash||HashFile(seed.Pak)!=seed.PackHash)
   throw new InvalidDataException("This seed's data changed or is incomplete. Restore its original assets before playing.");
  var original=File.ReadAllBytes(ActiveBasePack());var policy=ProgressionGuard.CheckBase(original);
  if(Hash(original)!=fresh.BaseHash)throw new InvalidDataException("This seed's original asset pack no longer matches the installation.");
  if(policy.ContentId!=fresh.ContentId)throw new InvalidDataException("This seed belongs to "+fresh.ContentName+", but a different game-data profile is selected.");
  if(fresh.Version>=4)StoryShuffleV4.Validate(original,File.ReadAllBytes(seed.Pak),fresh.Options);
  else ProgressionGuard.Validate(original,File.ReadAllBytes(seed.Pak),fresh.Options);
 }
 public static SeedRecord Generate(string seed,ShuffleOptions options,string? expectedBaseHash=null,int version=Version) {
  if(version is not (3 or Version))throw new InvalidDataException("This generator supports version 3 and 4 recipes.");
  if(version==3)options=options with {EnemyEncounters=false};
  seed=CleanSeed(seed);options.Validate();
  byte[] original=File.ReadAllBytes(ActiveBasePack());var policy=ProgressionGuard.CheckBase(original);
  string baseHash=Hash(original);
  if(expectedBaseHash!=null&&baseHash!=expectedBaseHash)throw new InvalidDataException("This recipe uses a different original asset pack; it cannot reproduce the same game here.");
  string id=Identity(seed,options,baseHash,policy.ContentId,version),folder=Path.Combine(Library,id);
  if(Directory.Exists(folder)) {
   var existing=Read(folder);Verify(existing);return existing; // never overwrite a seed or its saves
  }
  var built=version==3?BuildV3(original,seed,options):Build(original,seed,options);
  var record=new SeedRecord {Version=version,Seed=seed,Options=options,Id=id,ContentId=policy.ContentId,ContentName=policy.DisplayName,BaseHash=baseHash,PackHash=Hash(built.Pack),CreatedUtc=DateTime.UtcNow,Changes=built.Counts,Folder=folder};
  Directory.CreateDirectory(Library);
  string staging=Path.Combine(Library,".generating-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(staging);
  File.WriteAllBytes(Path.Combine(staging,"assets.pak"),built.Pack);
  File.WriteAllText(Path.Combine(staging,"spoiler.json"),JsonSerializer.Serialize(new {record.Generator,record.Version,record.ContentId,record.ContentName,record.Seed,record.Options,Changes=built.Spoiler},Settings.JsonOptions));
  File.WriteAllText(Path.Combine(staging,"recipe.ebseed.json"),JsonSerializer.Serialize(new SeedRecipe(Name,version,seed,options,baseHash,policy.ContentId,policy.DisplayName),Settings.JsonOptions));
  File.WriteAllText(Path.Combine(staging,"seed.json"),JsonSerializer.Serialize(record,Settings.JsonOptions));
  File.WriteAllText(Path.Combine(staging,"safety.json"),JsonSerializer.Serialize(version>=4?StoryShuffleV4.Report(original):ProgressionGuard.Report(original),Settings.JsonOptions));
  Directory.CreateDirectory(Path.Combine(staging,"Game","saves"));
  Directory.CreateDirectory(Path.Combine(staging,"Game","screenshots"));
  Directory.Move(staging,folder);return record;
 }
 public static SeedRecipe ImportRecipe(string path) {
  if(new FileInfo(path).Length>16_384)throw new InvalidDataException("Seed recipe is too large.");
  var recipe=JsonSerializer.Deserialize<SeedRecipe>(File.ReadAllText(path))??throw new InvalidDataException("Empty seed recipe.");
  CheckRecipe(recipe);return recipe.Version<4?recipe with {Options=recipe.Options with {EnemyEncounters=false}}:recipe;
 }
 static void CheckRecipe(SeedRecipe recipe,bool allowLegacy=false) {
  if(recipe.Generator!=Name||(recipe.Version is not (3 or Version)&&!(allowLegacy&&recipe.Version is 1 or 2))||recipe.Options==null)
   throw new InvalidDataException("Use a Companion Story Shuffle version 3 or 4 recipe. Older native seeds remain on disk for recovery; website ROMs and spoiler files are not supported native seeds.");
  if(recipe.Seed==null||CleanSeed(recipe.Seed)!=recipe.Seed||recipe.BaseHash==null||recipe.BaseHash.Length!=64||!recipe.BaseHash.All(Uri.IsHexDigit))
   throw new InvalidDataException("Invalid seed recipe.");
  if(recipe.Version>=3&&(string.IsNullOrWhiteSpace(recipe.ContentId)||string.IsNullOrWhiteSpace(recipe.ContentName)))throw new InvalidDataException("The seed recipe is missing its game-data profile.");
  recipe.Options.Validate();
  if(recipe.Version<4&&!recipe.Options.Gifts&&!recipe.Options.Shops&&!recipe.Options.EnemyStats&&!recipe.Options.EnemyDrops)throw new InvalidDataException("Enable at least one version 3 shuffle option.");
 }
 internal static void ValidatePack(byte[] pack) {
  if(pack.Length<44||!pack.AsSpan(0,44).SequenceEqual(Convert.FromHexString(Layout.Header)))
   throw new InvalidDataException("Story Shuffle needs the installed native asset layout.");
  int count=checked((int)BinaryPrimitives.ReadUInt32LittleEndian(pack.AsSpan(8))),blob=checked(44+count*8);
  if(pack.Length<blob)throw new InvalidDataException("Incomplete asset index.");
  for(int i=0;i<count;i++) {
   uint offset=BinaryPrimitives.ReadUInt32LittleEndian(pack.AsSpan(44+i*8));
   uint size=BinaryPrimitives.ReadUInt32LittleEndian(pack.AsSpan(48+i*8));
   if((ulong)offset+size>(ulong)(pack.Length-blob))throw new InvalidDataException("Invalid asset data range.");
  }
   foreach(var (name,size) in new[]{(Npcs,26928),(Items,9906)}) {
    var span=Range(pack,name);if(span.Length!=size)throw new InvalidDataException("Unexpected randomizer table size: "+name);
   }
   int shops=Range(pack,Shops).Length;
   if(shops is not (462 or 483))throw new InvalidDataException("Unexpected randomizer shop-table size.");
   var (enemyStart,enemyLength)=Range(pack,Enemies);
   const int enemyBytes=EnemyRecordCount*94;
   if(enemyLength!=enemyBytes) {
    if(enemyLength!=enemyBytes+12+EnemyRecordCount*4||!pack.AsSpan(enemyStart+enemyBytes,8).SequenceEqual("MRDXAI01"u8)||BinaryPrimitives.ReadUInt32LittleEndian(pack.AsSpan(enemyStart+enemyBytes+8))!=EnemyRecordCount)
     throw new InvalidDataException("Unexpected randomizer enemy-table extension.");
   }
  }
 internal static (int Start,int Length) Range(byte[] pack,string name) {
  int index=Layout.Assets[name];
  int count=checked((int)BinaryPrimitives.ReadUInt32LittleEndian(pack.AsSpan(8)));
  return (checked(44+count*8+(int)BinaryPrimitives.ReadUInt32LittleEndian(pack.AsSpan(44+index*8))),checked((int)BinaryPrimitives.ReadUInt32LittleEndian(pack.AsSpan(48+index*8))));
 }
 internal static ReadOnlySpan<byte> Table(byte[] pack,string name){var (start,length)=Range(pack,name);return pack.AsSpan(start,length);}
 internal static ShuffleBuild Build(byte[] original,string seed,ShuffleOptions options)=>StoryShuffleV4.Build(original,seed,options);
 internal static ShuffleBuild BuildV3(byte[] original,string seed,ShuffleOptions options) {
  seed=CleanSeed(seed);options.Validate();var policy=ProgressionGuard.CheckBase(original);var protectedItems=policy.Items;var protectedEnemies=policy.Enemies;
  byte[] output=(byte[])original.Clone();var spoiler=new List<ShuffleChange>();var counts=new Dictionary<string,int>();
  var catalog=new Item[254];var items=Table(original,Items);
  for(int i=0;i<catalog.Length;i++)catalog[i]=new(i,Text(items.Slice(i*39,25)),items[i*39+25],BinaryPrimitives.ReadUInt16LittleEndian(items.Slice(i*39+26)),items[i*39+28]);
  int Pick(int old,StableRandom random) {
   if(old<=0||old>=catalog.Length||!catalog[old].Optional(protectedItems))return old;
   var item=catalog[old];var pool=catalog.Where(i=>i.Optional(protectedItems)&&i.Kind==item.Kind&&(!item.Equipment||(i.Flags&15)==(item.Flags&15)));
   if(options.Mode=="Balanced")pool=pool.Where(i=>i.Cost>=Math.Max(1,item.Cost/2)&&i.Cost<=Math.Max(10,item.Cost*3/2));
   var candidates=pool.Where(i=>i.Id!=old).ToArray();return candidates.Length==0?old:candidates[random.Next(candidates.Length)].Id;
  }
  StableRandom Rng(string domain)=>new($"{Name}:3\n{seed}\n{options.Mode}\n{Hash(original)}\n{domain}");
  void Change(string table,int entry,int before,int after,string? description=null) {
   if(before==after)return;
   counts[table]=counts.GetValueOrDefault(table)+1;
   spoiler.Add(new(table,entry,description??catalog[before].Name,description==null?catalog[after].Name:$"{before} → {after}"));
  }
  if(options.Gifts) {
   var (start,length)=Range(output,Npcs);var random=Rng("gifts");
   for(int i=0;i<length/17;i++) {
    int p=start+i*17;if(output[p]!=2)continue;
    uint old=BinaryPrimitives.ReadUInt32LittleEndian(output.AsSpan(p+13));if(old>=254)continue; // money and out-of-range entries fixed
    int next=Pick((int)old,random);if(next==(int)old)continue;
     BinaryPrimitives.WriteUInt32LittleEndian(output.AsSpan(p+13),(uint)next);Change("Gifts",i,(int)old,next);
    }
   }
  if(options.Shops) {
   var (start,length)=Range(output,Shops);var random=Rng("shops");
   for(int shop=0;shop<length/7;shop++) {
    // Keep an affordable baseline. Protection of ALL quest/trade item slots
    // comes from the independently audited item policy, not slot position.
    for(int slot=1;slot<7;slot++) {
     int p=start+shop*7+slot,old=original[p];if(old==0)continue;
     int next=Pick(old,random);
     if(output.AsSpan(start+shop*7,7).Contains((byte)next))continue;
     output[p]=(byte)next;Change("Shop slots",shop,old,next);
    }
   }
  }
  if(options.EnemyStats||options.EnemyDrops) {
   var (start,length)=Range(output,Enemies);var stats=Rng("enemy stats");var drops=Rng("enemy drops");
   for(int i=1;i<EnemyRecordCount;i++) {
    int p=start+i*94;
    if(protectedEnemies.Contains(i)||original[p+86]!=0||original[p+54]==0)continue; // scripted battles, bosses and special records fixed
    string name=Text(original.AsSpan(p+1,25));
    if(options.EnemyStats) {
     int range=options.Mode=="Balanced"?15:30,percent=100-range+stats.Next(2*range+1);
     var details=new List<string>();
     foreach(var (offset,label) in new[]{(33,"HP"),(56,"Offense"),(58,"Defense")}) {
      int before=BinaryPrimitives.ReadUInt16LittleEndian(original.AsSpan(p+offset));
      if(offset!=33&&before>255)continue; // preserve unusual original records rather than changing their low-byte semantics
      int after=Math.Clamp((before*percent+50)/100,before>0?1:0,offset==33?65535:255);
      BinaryPrimitives.WriteUInt16LittleEndian(output.AsSpan(p+offset),(ushort)after);if(before!=after)details.Add($"{label} {before} → {after}");
     }
     int speed=original[p+60],speedAfter=Math.Clamp((speed*percent+50)/100,speed>0?1:0,255);output[p+60]=(byte)speedAfter;if(speed!=speedAfter)details.Add($"Speed {speed} → {speedAfter}");
     // Rewards remain original. Battle actions, scripted behavior, music, status and spawn tables remain original.
     if(details.Count>0){counts["Enemies"]=counts.GetValueOrDefault("Enemies")+1;spoiler.Add(new("Enemies",i,name,string.Join("; ",details)));}
    }
    if(options.EnemyDrops) {
     int old=original[p+88],next=Pick(old,drops);output[p+88]=(byte)next;
     if(old!=next){counts["Enemy drops"]=counts.GetValueOrDefault("Enemy drops")+1;spoiler.Add(new("Enemy drops",i,name+": "+catalog[old].Name,catalog[next].Name));}
    }
   }
  }
  if(counts.Count==0)throw new InvalidDataException("These options did not change any eligible data.");
  ProgressionGuard.Validate(original,output,options);
  return new(output,spoiler,counts);
 }
 internal static string Text(ReadOnlySpan<byte> encoded) {
  var text=new StringBuilder();foreach(byte b in encoded){if(b==0)break;if(b>=0x50&&b<=0xAD)text.Append((char)(b-0x30));}return text.ToString();
 }
 internal sealed record Item(int Id,string Name,byte Kind,int Cost,byte Flags) {
  public bool Equipment=>Kind is 0x10 or 0x11 or 0x14 or 0x18 or 0x1C;
  public bool Optional(HashSet<int> protectedItems)=>Id>0&&!protectedItems.Contains(Id)&&Cost>0&&!string.IsNullOrWhiteSpace(Name)&&(Equipment||Kind is 0x20 or 0x24 or 0x28 or 0x2C or 0x30);
 }
 // Fixed algorithm rather than System.Random: seed recipes survive runtime upgrades.
 internal sealed class StableRandom {
  uint state;
  public StableRandom(string seed){state=BinaryPrimitives.ReadUInt32LittleEndian(SHA256.HashData(Encoding.UTF8.GetBytes(seed)));if(state==0)state=0x9e3779b9;}
  uint Draw(){state^=state<<13;state^=state>>17;state^=state<<5;return state;}
  public int Next(int max){if(max<1)throw new ArgumentOutOfRangeException(nameof(max));uint bound=(uint)max,threshold=unchecked(0u-bound)%bound,n;do{n=Draw();}while(n<threshold);return (int)(n%bound);}
 }
}
