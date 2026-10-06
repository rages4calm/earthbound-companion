using System.Buffers.Binary;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace EarthBoundCompanion;

// Exact reviewed pack pairs only. Compare assets independently of changing
// offsets/sizes; never apply this to randomizer seeds or unknown patched data.
static class ReduxStoryUpgrade {
 internal const string NamesBeforeHash="62ba3d70b37c95812bc742b40f1f599b142263ffb39f3dd949ddc66aa7e246c2";
 internal const string GraphicsBeforeHash="ed299183d4b1aff4b38c56ef16da28a256c3a65d33ba1d9327c9b19df0272ef3";
 internal const string CurrentHash="3ed273eaedad5131a13dc07b6916377130857929854886b139b30a723482f8b9";
 internal static bool CanUpgrade(string hash)=>hash==NamesBeforeHash||hash==GraphicsBeforeHash;
 internal static void Physical(string path) {
  for(string? p=Path.GetFullPath(path);p!=null;p=Path.GetDirectoryName(p))
   if((File.Exists(p)||Directory.Exists(p))&&(File.GetAttributes(p)&FileAttributes.ReparsePoint)!=0)
    throw new IOException("Select an ordinary installation folder, without redirected paths.");
 }
 internal static string Validate(byte[] oldPack,byte[] newPack) {
  StoryShuffle.ValidatePack(oldPack);StoryShuffle.ValidatePack(newPack);
  string oldHash=StoryShuffle.Hash(oldPack),newHash=StoryShuffle.Hash(newPack);
  bool names=oldHash==NamesBeforeHash,graphics=newHash==CurrentHash;
  if(!((CanUpgrade(oldHash)&&graphics)||(names&&newHash==GraphicsBeforeHash)))
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
   if(!(graphics&&((i>=478&&i<=580)||i is 682 or 683 or 688 or 689))&&!(names&&i==122))throw new InvalidDataException("A non-art story asset changed during the update.");
   changed++;
  }
  if(changed!=(graphics?107:0)+(names?1:0))throw new InvalidDataException("The update differs from the reviewed asset changes.");
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
  if(!CanUpgrade(oldHash)||(newHash!=CurrentHash&&newHash!=GraphicsBeforeHash))throw new InvalidDataException("Unreviewed story-save upgrade.");
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
