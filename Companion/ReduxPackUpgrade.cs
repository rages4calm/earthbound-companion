using System.Buffers.Binary;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace EarthBoundCompanion;

// Exact reviewed pack pairs only. Compare assets independently of changing
// offsets/sizes; never apply this to randomizer seeds or unknown patched data.
static class ReduxStoryUpgrade {
 internal const string NamesBeforeHash="62ba3d70b37c95812bc742b40f1f599b142263ffb39f3dd949ddc66aa7e246c2";
 internal const string GraphicsBeforeHash="ed299183d4b1aff4b38c56ef16da28a256c3a65d33ba1d9327c9b19df0272ef3";
 internal const string BattleGraphicsHash="3ed273eaedad5131a13dc07b6916377130857929854886b139b30a723482f8b9";
 internal const string LegacyCurrentHash="d9a772d10aff68bdf93c077cda640d42b835884d6834bb18bf0d43c3800f57bb";
 internal const string CurrentHash="4b5f1c5ac76e4bdcce2dc66a2e8ef95b659e561d3cadebefa66efb85c0be5236";
 // Native dev.31 repairs the two known old cast tables at runtime. Existing
 // installations keep their content identity and saves; fresh setup is fixed.
 internal static bool IsCurrent(string hash)=>hash==CurrentHash||hash==LegacyCurrentHash;
 internal static bool CanUpgrade(string hash)=>hash==NamesBeforeHash||hash==GraphicsBeforeHash||hash==BattleGraphicsHash||hash==LegacyCurrentHash;
 static bool ReviewedPair(string oldHash,string newHash)=>
  (CanUpgrade(oldHash)&&IsCurrent(newHash)&&oldHash!=newHash)||
  ((oldHash==NamesBeforeHash||oldHash==GraphicsBeforeHash)&&newHash==BattleGraphicsHash)||
  (oldHash==NamesBeforeHash&&newHash==GraphicsBeforeHash);
 internal static void Physical(string path) {
  for(string? p=Path.GetFullPath(path);p!=null;p=Path.GetDirectoryName(p))
   if((File.Exists(p)||Directory.Exists(p))&&(File.GetAttributes(p)&FileAttributes.ReparsePoint)!=0)
    throw new IOException("Select an ordinary installation folder, without redirected paths.");
 }
 internal static string Validate(byte[] oldPack,byte[] newPack) {
  StoryShuffle.ValidatePack(oldPack);StoryShuffle.ValidatePack(newPack);
  string oldHash=StoryShuffle.Hash(oldPack),newHash=StoryShuffle.Hash(newPack);
  bool names=oldHash==NamesBeforeHash,presentation=IsCurrent(newHash)&&oldHash!=LegacyCurrentHash;
  bool graphics=(presentation||newHash==BattleGraphicsHash)&&oldHash!=BattleGraphicsHash;
  bool castFix=newHash==CurrentHash;
  if(!ReviewedPair(oldHash,newHash))
   throw new InvalidDataException("This upgrade supports only the reviewed Redux story packs. Keep other editions and randomizer seeds with their original data.");
  if(!oldPack.AsSpan(0,44).SequenceEqual(newPack.AsSpan(0,44)))throw new InvalidDataException("The native asset registry changed.");
  int count=checked((int)BinaryPrimitives.ReadUInt32LittleEndian(newPack.AsSpan(8))),body=checked(44+count*8),changed=0;
  ReadOnlySpan<byte> Asset(byte[] pack,int index) {
   int start=checked(body+(int)BinaryPrimitives.ReadUInt32LittleEndian(pack.AsSpan(44+index*8)));
   int size=checked((int)BinaryPrimitives.ReadUInt32LittleEndian(pack.AsSpan(48+index*8)));
   return pack.AsSpan(start,size);
  }
  for(int i=0;i<count;i++) {
   if(Asset(oldPack,i).SequenceEqual(Asset(newPack,i)))continue;
   // IDs 478..580 are the 103 battle_bgs/graphics entries in the pinned
   // registry; IDs 682/683/688/689 are palettes 101/102/107/108 whose
   // relocated consumers changed depth. ID 122 is the reviewed PSI names.
   // IDs 55/56 are gas-station arrangement/graphics, 159 Starman Jr teleport,
   // and 71/1168..1173 the Town Map label and six map assets. The listed
   // 31 swirl IDs differ at the source decoded scanline masks; the other
   // 95 swirl assets remain byte-identical.
   if(castFix&&i==150) {
    if(!Asset(newPack,i).SequenceEqual(new byte[]{0x80,1,0x90,1,0xa0,1,0xb0,1}))throw new InvalidDataException("The corrected cast table differs from its source layout.");
   } else if(!(graphics&&((i>=478&&i<=580)||i is 682 or 683 or 688 or 689))&&!(names&&i==122)&&!(presentation&&(i is 55 or 56 or 71 or 159 or 1047 or 1051 or 1053 or 1055 or 1059 or 1081 or 1083 or 1086 or 1087 or 1088 or 1090 or 1091 or 1092 or 1094 or 1095 or 1096 or 1098 or 1099 or 1100 or 1102 or 1103 or 1104 or 1105 or 1106 or 1107 or 1108 or 1109 or 1110 or 1111 or 1112 or 1119||(i>=1168&&i<=1173))))throw new InvalidDataException("A non-art story asset changed during the update.");
   changed++;
  }
  if(changed!=(graphics?107:0)+(names?1:0)+(presentation?41:0)+(castFix?1:0))throw new InvalidDataException("The update differs from the reviewed asset changes.");
  return oldHash;
 }
 internal static int Import(string previousRoot) {
  previousRoot=Path.GetFullPath(previousRoot);Physical(previousRoot);Physical(Settings.Root);
  if(previousRoot.TrimEnd(Path.DirectorySeparatorChar).Equals(Settings.Root.TrimEnd(Path.DirectorySeparatorChar),StringComparison.OrdinalIgnoreCase))
   throw new InvalidDataException("Select the separate previous installation. Updating this installation is available from Game Mode.");
  string previousPack=Path.Combine(previousRoot,"Profiles",ReduxProfileService.ContentId,"assets.pak");
  Physical(previousPack);Physical(ReduxProfileService.Pack);
  byte[] oldPack=File.ReadAllBytes(previousPack),newPack=File.ReadAllBytes(ReduxProfileService.Pack);
  string oldHash=Validate(oldPack,newPack);
  return CopyStorySaves(previousRoot,oldHash,StoryShuffle.Hash(newPack),true);
 }
 internal static int CopyStorySaves(string previousRoot,string oldHash,string newHash,bool required) {
  if(!ReviewedPair(oldHash,newHash))throw new InvalidDataException("Unreviewed story-save upgrade.");
  string source=Path.Combine(previousRoot,"UserData","ContentProfiles",oldHash,"Game","saves");Physical(source);
  var files=new Dictionary<string,byte[]>();
  if(Directory.Exists(source))foreach(string path in Directory.EnumerateFiles(source)) {
   string name=Path.GetFileName(path);
   if(name!="earthbound.srm"&&!Regex.IsMatch(name,@"\Aquicksave_[1-5]\.bin\.[01]\z",RegexOptions.CultureInvariant))continue;
   Physical(path);var info=new FileInfo(path);
   if(info.Length<=0||info.Length>4_000_000)throw new InvalidDataException("A previous story save has an unsupported size.");
   byte[] bytes=File.ReadAllBytes(path);
   if(name=="earthbound.srm"&&bytes.Length!=8192)throw new InvalidDataException("The previous phone save has an unexpected size.");
   if(name.StartsWith("quicksave_")&&!SaveRecovery.ValidQuick(bytes))throw new InvalidDataException("A previous quick save is damaged or needs another native state format.");
   files.Add(name,bytes);
  }
  if(files.Count==0){if(required)throw new InvalidDataException("No supported Redux story saves were found in that installation.");return 0;}
  string game=Path.Combine(Settings.User,"ContentProfiles",newHash,"Game"),target=Path.Combine(game,"saves"),receipt=Path.Combine(game,"redux-story-import.json");
  Physical(game);Physical(target);Physical(receipt);
  if((Directory.Exists(target)&&Directory.EnumerateFileSystemEntries(target).Any())||File.Exists(receipt))
   throw new IOException("The updated story already has saves or an import receipt. Use a fresh destination so nothing is overwritten.");
  Directory.CreateDirectory(target);var created=new List<string>();
  try {
   foreach(var file in files){string path=Path.Combine(target,file.Key);using(var output=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.None)){created.Add(path);output.Write(file.Value);}}
   byte[] metadata=JsonSerializer.SerializeToUtf8Bytes(new{PreviousContentHash=oldHash,CurrentContentHash=newHash,Files=files.Select(f=>new{Name=f.Key,Sha256=StoryShuffle.Hash(f.Value)}),OriginalSavesPreserved=true,RandomizerSeedsImported=false},Settings.JsonOptions);
   using var outputReceipt=new FileStream(receipt,FileMode.CreateNew,FileAccess.Write,FileShare.None);created.Add(receipt);outputReceipt.Write(metadata);
  } catch {foreach(string path in created)File.Delete(path);throw;}
  return files.Count;
 }
}
