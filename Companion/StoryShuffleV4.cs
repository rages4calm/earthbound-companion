using System.Buffers.Binary;
namespace EarthBoundCompanion;

// V3 remains frozen in Randomizer.cs. V4 changes loot across categories and
// replaces wild placement references, never the battle groups used by scripts.
static class StoryShuffleV4 {
 internal const string Placements="data/enemy_placement_groups.bin",PlacementPointers="data/enemy_placement_groups_ptr_table.bin",BattlePointers="data/btl_entry_ptr_table.bin",Groups="data/enemy_battle_groups_table.bin";
 // Source-reviewed Monkey Cave requests. Keep vendor slots, rather than every
 // occurrence of each food. Pizza delivery and the egg-giving monkey's scripts
 // are immutable; retain the pizza gifts as an additional local supply.
 internal static readonly HashSet<int> TradeStock=[90,92,93,95,108,127,140,190,224];
 internal static readonly HashSet<int> QuestHelpers=[1,105,139,166,184];
 internal static StoryShuffle.Item[] Catalog(byte[] pack) {
  var table=StoryShuffle.Table(pack,StoryShuffle.Items);var result=new StoryShuffle.Item[254];
  for(int i=0;i<result.Length;i++)result[i]=new(i,StoryShuffle.Text(table.Slice(i*39,25)),table[i*39+25],BinaryPrimitives.ReadUInt16LittleEndian(table.Slice(i*39+26)),table[i*39+28]);
  return result;
 }
 internal static bool StoryItem(StoryShuffle.Item item)=>QuestHelpers.Contains(item.Id)||(item.Kind&0x3C)==0x38;
 internal static bool Loot(StoryShuffle.Item item)=>item.Id>0&&!StoryItem(item)&&!string.IsNullOrWhiteSpace(item.Name)&&item.Kind is 4 or 8 or 0x10 or 0x11 or 0x14 or 0x18 or 0x1C or 0x20 or 0x24 or 0x28 or 0x2C or 0x30 or 0x34 or 0x35;
 internal static int Value(StoryShuffle.Item item)=>item.Cost>0?item.Cost:item.Equipment?10000:item.Kind==8?1000:100;
 internal static bool GiftFixed(int id,StoryShuffle.Item[] catalog)=>id==0||(id<254&&(!Loot(catalog[id])||id==95));
 internal static bool ShopFixed(int id,StoryShuffle.Item[] catalog)=>id==0||!Loot(catalog[id])||TradeStock.Contains(id);
 internal sealed record Encounter(int Id,int Level,int Hp,int Count,string Name);
 internal sealed record Placement(int Offset,int Group);
 internal static List<Placement> PlacementSlots(byte[] pack) {
  var pointers=StoryShuffle.Table(pack,PlacementPointers);var data=StoryShuffle.Table(pack,Placements);
  if(pointers.Length!=203*4)throw new InvalidDataException("Unexpected wild placement registry.");
  var result=new Dictionary<int,Placement>();
  for(int i=1;i<pointers.Length/4;i++) {
   int at=checked((int)(BinaryPrimitives.ReadUInt32LittleEndian(pointers.Slice(i*4))&0xFFFFFF)-0xD0BBAC);
   if(at<0||at+4>data.Length)throw new InvalidDataException("Invalid wild placement pointer.");
   var rates=new[]{data[at+2],data[at+3]};at+=4;
   foreach(int rate in rates) {
    if(rate==0)continue;
    if(rate>100)throw new InvalidDataException("Invalid spawn chance.");
    int weight=0;
    while(weight<8) {
     if(at+3>data.Length||weight+data[at]>8)throw new InvalidDataException("Invalid wild encounter weights.");
     weight+=data[at];int group=BinaryPrimitives.ReadUInt16LittleEndian(data.Slice(at+1));
     if(data[at]>0)result[at+1]=new(at+1,group);at+=3;
    }
   }
  }
  return result.Values.OrderBy(p=>p.Offset).ToList();
 }
 internal static Dictionary<int,Encounter> Encounters(byte[] pack,List<Placement> slots) {
  var pointers=StoryShuffle.Table(pack,BattlePointers);var groups=StoryShuffle.Table(pack,Groups);var enemies=StoryShuffle.Table(pack,StoryShuffle.Enemies);
  var result=new Dictionary<int,Encounter>();
  foreach(int id in slots.Select(s=>s.Group).Distinct().Order()) {
   if(id*8+8>pointers.Length)throw new InvalidDataException("Invalid wild battle reference.");
   int at=checked((int)(BinaryPrimitives.ReadUInt32LittleEndian(pointers.Slice(id*8))&0xFFFFFF)-0xD0D52D);
   // Event escape rules are not candidates for a different wild encounter.
   bool ordinary=BinaryPrimitives.ReadUInt16LittleEndian(pointers.Slice(id*8+4))==0;
   int level=0,hp=0,count=0;var labels=new List<string>();
   while(true) {
    if(at<0||at>=groups.Length)throw new InvalidDataException("Invalid battle group pointer.");
    int n=groups[at];if(n==255)break;
    if(at+3>groups.Length)throw new InvalidDataException("Invalid battle group record.");
    if(n==0){at+=3;continue;} // Authored zero-count members are legal.
    int enemy=BinaryPrimitives.ReadUInt16LittleEndian(groups.Slice(at+1));
    if(enemy<=0||enemy>=231)throw new InvalidDataException("Invalid enemy ID.");
    int p=enemy*94;count+=n;level=Math.Max(level,enemies[p+54]);hp+=n*BinaryPrimitives.ReadUInt16LittleEndian(enemies.Slice(p+33));
    // Boss death behavior, special records and zero-level actors stay outside
    // the candidate pool. The original group and its flags are never edited.
    ordinary&=enemies[p+86]==0&&enemies[p+54]>0;
    labels.Add(n+" × "+StoryShuffle.Text(enemies.Slice(p+1,25)));at+=3;
   }
   if(ordinary&&count is >0 and <=7&&hp>0)result.Add(id,new(id,level,hp,count,string.Join(", ",labels)));
  }
  return result;
 }
 internal static bool Comparable(Encounter before,Encounter after,string mode) {
  int span=mode=="Balanced"?Math.Max(3,before.Level/5):Math.Max(6,before.Level/3);
  // Early-area replacements must not accidentally triple party size/HP.
  return Math.Abs(before.Level-after.Level)<=span&&after.Count<=Math.Max(2,before.Count+1)&&after.Hp>=Math.Max(1,before.Hp/2)&&after.Hp<=before.Hp*2;
 }
 internal static object Report(byte[] pack) {
  var policy=ProgressionGuard.CheckBase(pack);var items=Catalog(pack);var slots=PlacementSlots(pack);var groups=Encounters(pack,slots);
  return new {Version=4,policy.ContentId,policy.DisplayName,Status="Passed story and source preservation checks",ProtectedItems=items.Where(StoryItem).Select(i=>i.Id).ToArray(),RetainedTradeShopItems=TradeStock.Order().ToArray(),RetainedPizzaGifts=true,
   Checks=new[]{"Story keys and quest helpers retained; none introduced as random loot","Monkey Cave vendor sources, pizza gifts, delivery and NPC grants retained","Wild placement references randomized within level, HP and party-size bounds","Battle groups, boss lineups, AI, maps, flags, scripts, prices and drop chances unchanged","All other bytes and disabled options checked before launch"},WildPlacementSlots=slots.Count,EligibleEncounterGroups=groups.Count,FullPlaythroughVerified=false};
 }
 internal static ShuffleBuild Build(byte[] original,string seed,ShuffleOptions options) {
  seed=StoryShuffle.CleanSeed(seed);options.Validate();var policy=ProgressionGuard.CheckBase(original);
  var items=Catalog(original);byte[] output=(byte[])original.Clone();var changes=new List<ShuffleChange>();var counts=new Dictionary<string,int>();
  StoryShuffle.StableRandom Rng(string domain)=>new($"{StoryShuffle.Name}:4\n{seed}\n{options.Mode}\n{StoryShuffle.Hash(original)}\n{domain}");
  void Log(string table,int entry,string before,string after) {counts[table]=counts.GetValueOrDefault(table)+1;changes.Add(new(table,entry,before,after));}
  int Pick(int old,StoryShuffle.StableRandom rng,bool money=false,bool shop=false) {
   int value=money?Math.Max(1,old-256):Value(items[old]);
   var pool=items.Where(i=>Loot(i)&&i.Id!=27&&i.Id!=old&&(!shop||i.Cost>0));
   if(options.Mode=="Balanced")pool=pool.Where(i=>Value(i)>=Math.Max(1,value/2)&&Value(i)<=Math.Max(10,value*3/2));
   var eligible=pool.ToArray();return eligible.Length==0?old:eligible[rng.Next(eligible.Length)].Id;
  }
  if(options.Gifts) {
   var (start,length)=StoryShuffle.Range(original,StoryShuffle.Npcs);var rng=Rng("gifts");
   for(int i=0;i<length/17;i++) {
    int p=start+i*17;if(original[p]!=2)continue;
    uint raw=BinaryPrimitives.ReadUInt32LittleEndian(original.AsSpan(p+13));
    if(raw>int.MaxValue||raw is 254 or 255||GiftFixed((int)raw,items))continue;
    int old=(int)raw,next=Pick(old,rng,old>=256);if(next==old)continue;
    BinaryPrimitives.WriteUInt32LittleEndian(output.AsSpan(p+13),(uint)next);Log("Gifts",i,old>=256?"$"+(old-256):items[old].Name,items[next].Name);
   }
  }
  if(options.Shops) {
   var (start,length)=StoryShuffle.Range(original,StoryShuffle.Shops);var rng=Rng("shops");
   for(int i=0;i<length;i++) {
    int old=original[start+i];if(ShopFixed(old,items))continue;
    int next=Pick(old,rng,shop:true);if(next==old)continue;
    output[start+i]=(byte)next;Log("Shop slots",i,items[old].Name,items[next].Name);
   }
  }
  var (enemyStart,_)=StoryShuffle.Range(original,StoryShuffle.Enemies);var stats=Rng("enemy stats");var drops=Rng("enemy drops");
  for(int i=1;i<231;i++) {
   int p=enemyStart+i*94;if(original[p+86]!=0||original[p+54]==0)continue;
   string name=StoryShuffle.Text(original.AsSpan(p+1,25));
   if(options.EnemyStats&&!policy.Enemies.Contains(i)) {
    int range=options.Mode=="Balanced"?15:30,percent=100-range+stats.Next(range*2+1);var details=new List<string>();
    foreach(var (offset,label) in new[]{(33,"HP"),(56,"Offense"),(58,"Defense"),(60,"Speed")}) {
     int before=offset==60?original[p+offset]:BinaryPrimitives.ReadUInt16LittleEndian(original.AsSpan(p+offset));
     if(offset!=33&&before>255)continue;
     int after=Math.Clamp((before*percent+50)/100,before>0?1:0,offset==33?65535:255);
     if(offset==60)output[p+offset]=(byte)after;else BinaryPrimitives.WriteUInt16LittleEndian(output.AsSpan(p+offset),(ushort)after);
     if(before!=after)details.Add($"{label} {before} → {after}");
    }
    if(details.Count>0)Log("Enemies",i,name,string.Join("; ",details));
   }
   int old=original[p+88];
   if(options.EnemyDrops&&Loot(items[old])) {int next=Pick(old,drops);if(next!=old){output[p+88]=(byte)next;Log("Enemy drops",i,name+": "+items[old].Name,items[next].Name);}}
  }
  if(options.EnemyEncounters) {
   var slots=PlacementSlots(original);var encounters=Encounters(original,slots);var rng=Rng("wild encounters");var (start,_)=StoryShuffle.Range(original,Placements);
   foreach(var slot in slots) {
    if(!encounters.TryGetValue(slot.Group,out var before))continue;
    var pool=encounters.Values.Where(e=>e.Id!=before.Id&&e.Name!=before.Name&&Comparable(before,e,options.Mode)).ToArray();
    if(pool.Length==0)continue;var next=pool[rng.Next(pool.Length)];
    BinaryPrimitives.WriteUInt16LittleEndian(output.AsSpan(start+slot.Offset),(ushort)next.Id);Log("Wild encounters",slot.Offset,before.Name,next.Name);
   }
  }
  if(counts.Count==0)throw new InvalidDataException("These options did not change any eligible data.");
  Validate(original,output,options);return new(output,changes,counts);
 }
 // Independent byte whitelist: this validates permissible changes without
 // rerunning Pick or trusting a spoiler log or the generator's counters.
 internal static void Validate(byte[] original,byte[] candidate,ShuffleOptions options) {
  options.Validate();var policy=ProgressionGuard.CheckBase(original);StoryShuffle.ValidatePack(candidate);
  void Require(bool value,string reason){if(!value)throw new InvalidDataException("Story Shuffle v4 safety check failed: "+reason);}
  Require(original.Length==candidate.Length,"pack size changed");var allowed=new bool[original.Length];var items=Catalog(original);
  void Replacement(int old,int next,bool money=false,bool shop=false) {
   if(old==next)return;
   Require(next>0&&next<254&&Loot(items[next])&&next!=27,"invalid or story loot");
   if(shop)Require(items[next].Cost>0,"priceless shop replacement");
   if(options.Mode=="Balanced") {
    int value=money?Math.Max(1,old-256):Value(items[old]),cost=Value(items[next]);
    Require(cost>=Math.Max(1,value/2)&&cost<=Math.Max(10,value*3/2),"Balanced loot value exceeded");
   }
  }
  var (npcStart,npcLength)=StoryShuffle.Range(original,StoryShuffle.Npcs);
  for(int i=0;i<npcLength/17;i++) {
   int p=npcStart+i*17;uint raw=BinaryPrimitives.ReadUInt32LittleEndian(original.AsSpan(p+13));
   if(!options.Gifts||original[p]!=2||raw>int.MaxValue||raw is 254 or 255||GiftFixed((int)raw,items))continue;
   uint next=BinaryPrimitives.ReadUInt32LittleEndian(candidate.AsSpan(p+13));Require(next<=int.MaxValue,"invalid gift");Replacement((int)raw,(int)next,raw>=256);
   for(int k=13;k<17;k++)allowed[p+k]=true;
  }
  var (shopStart,shopLength)=StoryShuffle.Range(original,StoryShuffle.Shops);
  for(int i=0;i<shopLength;i++)if(options.Shops&&!ShopFixed(original[shopStart+i],items)){Replacement(original[shopStart+i],candidate[shopStart+i],shop:true);allowed[shopStart+i]=true;}
  var (enemyStart,_)=StoryShuffle.Range(original,StoryShuffle.Enemies);
  for(int i=1;i<231;i++) {
   int p=enemyStart+i*94;if(original[p+86]!=0||original[p+54]==0)continue;
   if(options.EnemyStats&&!policy.Enemies.Contains(i))foreach(int offset in new[]{33,56,58,60}) {
    int before=offset==60?original[p+offset]:BinaryPrimitives.ReadUInt16LittleEndian(original.AsSpan(p+offset));if(offset!=33&&before>255)continue;
    int after=offset==60?candidate[p+offset]:BinaryPrimitives.ReadUInt16LittleEndian(candidate.AsSpan(p+offset)),range=options.Mode=="Balanced"?15:30,cap=offset==33?65535:255;
    Require(after>=Math.Clamp((before*(100-range)+50)/100,before>0?1:0,cap)&&after<=Math.Clamp((before*(100+range)+50)/100,before>0?1:0,cap),"enemy stat bounds exceeded");
    allowed[p+offset]=true;if(offset!=60)allowed[p+offset+1]=true;
   }
   if(options.EnemyDrops&&Loot(items[original[p+88]])){Replacement(original[p+88],candidate[p+88]);allowed[p+88]=true;}
  }
  if(options.EnemyEncounters) {
   var slots=PlacementSlots(original);var encounters=Encounters(original,slots);var (start,_)=StoryShuffle.Range(original,Placements);
   foreach(var slot in slots) {
    if(!encounters.TryGetValue(slot.Group,out var before))continue;
    int next=BinaryPrimitives.ReadUInt16LittleEndian(candidate.AsSpan(start+slot.Offset));
    Require(encounters.TryGetValue(next,out var after)&&Comparable(before,after,options.Mode),"invalid or oversized wild encounter");
    allowed[start+slot.Offset]=allowed[start+slot.Offset+1]=true;
   }
  }
  for(int i=0;i<original.Length;i++)if(!allowed[i]&&candidate[i]!=original[i])Require(false,"protected byte changed at "+i);
 }
}
