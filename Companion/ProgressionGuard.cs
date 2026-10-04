using System.Buffers.Binary;
using System.Text.Json;

namespace EarthBoundCompanion;

internal sealed record ProgressionPolicy(string BaseHash, int[] ProtectedItems, int[] ProtectedEnemies,int SaveStateVersion,uint SaveStateCrcPolynomial);

// A conservative invariant check for the unchanged original story. Independent
// of the generator's Pick function; invoked at generation AND before launch.
static class ProgressionGuard {
 static readonly ProgressionPolicy Policy = Load();
 internal static readonly HashSet<int> Items = Policy.ProtectedItems.ToHashSet();
 internal static readonly HashSet<int> Enemies = Policy.ProtectedEnemies.ToHashSet();
 internal static int SaveStateVersion=>Policy.SaveStateVersion;
 internal static uint SaveStateCrcPolynomial=>Policy.SaveStateCrcPolynomial;
 static ProgressionPolicy Load() {
  using var stream=typeof(ProgressionGuard).Assembly.GetManifestResourceStream("EarthBoundCompanion.progression-policy.json")
   ?? typeof(ProgressionGuard).Assembly.GetManifestResourceNames().Where(n=>n.EndsWith("progression-policy.json")).Select(n=>typeof(ProgressionGuard).Assembly.GetManifestResourceStream(n)).FirstOrDefault()
   ?? throw new InvalidDataException("Progression protection registry is missing.");
  return JsonSerializer.Deserialize<ProgressionPolicy>(stream)??throw new InvalidDataException("Empty progression protection registry.");
 }
 internal static void CheckBase(byte[] original) {
  StoryShuffle.ValidatePack(original);
  if(StoryShuffle.Hash(original)!=Policy.BaseHash)throw new InvalidDataException("Story Shuffle needs the original asset pack used by this edition's progression audit. Restore Game/assets.pak before generating or playing a seed.");
 }
 internal static object Report()=>new {
  Status="Passed original-story preservation checks", Policy="Original story dependencies, not shuffled-world logic", ProtectedItemCount=Items.Count,
  ProtectedScriptedEnemyCount=Enemies.Count, ProtectedItems=Items.Order().ToArray(), ProtectedEnemies=Enemies.Order().ToArray(),
  Checks=new[]{"Original maps, doors, scripts, flags, prices, rewards, starting items and item behavior unchanged", "Every original source of a protected item retained", "Scripted battles and bosses unchanged", "Replacement equipment compatible with original users", "Stat ranges and native bounds checked"},
  FullPlaythroughVerified=false
 };
 internal static void Validate(byte[] original,byte[] candidate,ShuffleOptions options) {
  CheckBase(original);StoryShuffle.ValidatePack(candidate);
  void Require(bool value,string reason) {if(!value)throw new InvalidDataException("Progression safety check failed: "+reason+". Keep this seed's saves for recovery; generate a new version 2 seed to play.");}
  Require(original.Length==candidate.Length,"asset pack size changed");
  var allowed=new bool[original.Length];var items=StoryShuffle.Table(original,StoryShuffle.Items).ToArray();
  bool Eligible(int id)=>id>0&&id<254&&!Items.Contains(id)&&BinaryPrimitives.ReadUInt16LittleEndian(items.AsSpan(id*39+26))>0&&items[id*39+25] is 0x10 or 0x11 or 0x14 or 0x18 or 0x1C or 0x20 or 0x24 or 0x28 or 0x2C or 0x30;
  void Replacement(int before,int after) {
   Require(Eligible(after),"replacement uses a protected or ineligible item");
   Require(items[before*39+25]==items[after*39+25],"replacement changed the item category");
   if(items[before*39+25]<0x20)Require((items[before*39+28]&15)==(items[after*39+28]&15),"equipment changed its usable characters");
   if(options.Mode=="Balanced") {
    int cost=BinaryPrimitives.ReadUInt16LittleEndian(items.AsSpan(before*39+26)),next=BinaryPrimitives.ReadUInt16LittleEndian(items.AsSpan(after*39+26));
    Require(next>=Math.Max(1,cost/2)&&next<=Math.Max(10,cost*3/2),"replacement broke the Balanced price range");
   }
  }
  var (npcStart,npcLength)=StoryShuffle.Range(original,StoryShuffle.Npcs);
  for(int i=0;i<npcLength/17;i++) {
   int p=npcStart+i*17;uint before=BinaryPrimitives.ReadUInt32LittleEndian(original.AsSpan(p+13));
   if(!options.Gifts||original[p]!=2||before>=254||!Eligible((int)before))continue;
   uint after=BinaryPrimitives.ReadUInt32LittleEndian(candidate.AsSpan(p+13));Require(after<254,"gift gained an invalid item");Replacement((int)before,(int)after);
   for(int k=13;k<17;k++)allowed[p+k]=true;
  }
  var (shopStart,shopLength)=StoryShuffle.Range(original,StoryShuffle.Shops);
  for(int i=0;i<shopLength;i++) {
   int p=shopStart+i;if(!options.Shops||i%7==0||!Eligible(original[p]))continue;
   Replacement(original[p],candidate[p]);allowed[p]=true;
  }
  var (enemyStart,enemyLength)=StoryShuffle.Range(original,StoryShuffle.Enemies);
  for(int i=1;i<enemyLength/94;i++) {
   int p=enemyStart+i*94;if(Enemies.Contains(i)||original[p+86]!=0||original[p+54]==0)continue;
   if(options.EnemyStats) {
    int range=options.Mode=="Balanced"?15:30;
    foreach(int offset in new[]{33,56,58}) {
     int before=BinaryPrimitives.ReadUInt16LittleEndian(original.AsSpan(p+offset));
     if(offset!=33&&before>255)continue;
     int after=BinaryPrimitives.ReadUInt16LittleEndian(candidate.AsSpan(p+offset)),cap=offset==33?65535:255;
     Require(after>=Math.Clamp((before*(100-range)+50)/100,before>0?1:0,cap)&&after<=Math.Clamp((before*(100+range)+50)/100,before>0?1:0,cap),"enemy statistic exceeded its bounds");
     allowed[p+offset]=allowed[p+offset+1]=true;
    }
    int speed=original[p+60],next=candidate[p+60];
    Require(next>=Math.Clamp((speed*(100-range)+50)/100,speed>0?1:0,255)&&next<=Math.Clamp((speed*(100+range)+50)/100,speed>0?1:0,255),"enemy speed exceeded its bounds");allowed[p+60]=true;
   }
   if(options.EnemyDrops&&Eligible(original[p+88])){Replacement(original[p+88],candidate[p+88]);allowed[p+88]=true;}
  }
  // This covers all assets, not just the four shuffled tables. No script,
  // door, event, quest gift, trade source, or disabled option may change.
  for(int i=0;i<original.Length;i++)if(!allowed[i]&&candidate[i]!=original[i])Require(false,"a protected byte changed at "+i);
 }
}
