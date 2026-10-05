using System.Buffers.Binary;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace EarthBoundCompanion;

// A single audited names-only upgrade. Seeds and other content pairs are excluded.
static class ReduxStoryUpgrade {
 internal const string PreviousHash="62ba3d70b37c95812bc742b40f1f599b142263ffb39f3dd949ddc66aa7e246c2";
 internal const string CurrentHash="ed299183d4b1aff4b38c56ef16da28a256c3a65d33ba1d9327c9b19df0272ef3";
 static void Physical(string path) {
  for(string? p=Path.GetFullPath(path);p!=null;p=Path.GetDirectoryName(p))
   if((File.Exists(p)||Directory.Exists(p))&&(File.GetAttributes(p)&FileAttributes.ReparsePoint)!=0)
    throw new IOException("Select an ordinary installation folder, without redirected paths.");
 }
 internal static int Import(string previousRoot) {
  previousRoot=Path.GetFullPath(previousRoot);Physical(previousRoot);Physical(Settings.Root);
  if(previousRoot.TrimEnd(Path.DirectorySeparatorChar).Equals(Settings.Root.TrimEnd(Path.DirectorySeparatorChar),StringComparison.OrdinalIgnoreCase))
   throw new InvalidDataException("Keep the previous installation separate; select its folder here.");
  string previousPack=Path.Combine(previousRoot,"Profiles",ReduxProfileService.ContentId,"assets.pak");
  Physical(previousPack);Physical(ReduxProfileService.Pack);
  byte[] oldPack=File.ReadAllBytes(previousPack),newPack=File.ReadAllBytes(ReduxProfileService.Pack);
  if(StoryShuffle.Hash(oldPack)!=PreviousHash||StoryShuffle.Hash(newPack)!=CurrentHash)
   throw new InvalidDataException("This import supports only the audited dev.2 to dev.3 Redux story update. Other editions and randomizer seeds need their original installations.");
  // The two fixed hashes identify the reviewed packs; additionally verify that
  // all changed bytes are inside the 425-byte relocated PSI-name asset.
  const int psiIndex=122;int body=44+checked((int)BinaryPrimitives.ReadUInt32LittleEndian(newPack.AsSpan(8))*8);
  int start=body+checked((int)BinaryPrimitives.ReadUInt32LittleEndian(newPack.AsSpan(44+psiIndex*8)));
  int size=checked((int)BinaryPrimitives.ReadUInt32LittleEndian(newPack.AsSpan(48+psiIndex*8)));
  if(size!=425||oldPack.Length!=newPack.Length||!oldPack.AsSpan(0,start).SequenceEqual(newPack.AsSpan(0,start))||!oldPack.AsSpan(start+size).SequenceEqual(newPack.AsSpan(start+size)))
   throw new InvalidDataException("The update contains changes beyond the audited PSI names.");
  string source=Path.Combine(previousRoot,"UserData","ContentProfiles",PreviousHash,"Game","saves");Physical(source);
  var files=new Dictionary<string,byte[]>();
  foreach(string path in Directory.EnumerateFiles(source)) {
   string name=Path.GetFileName(path);
   if(name!="earthbound.srm"&&!Regex.IsMatch(name,@"^quicksave_[1-5]\.bin\.[01]$"))continue;
   Physical(path);byte[] bytes=File.ReadAllBytes(path);
   if(name=="earthbound.srm"&&bytes.Length!=8192)throw new InvalidDataException("The previous phone save has an unexpected size.");
   if(name.StartsWith("quicksave_")&&(bytes.Length<20||!bytes.AsSpan(0,4).SequenceEqual("EBSD"u8)||BinaryPrimitives.ReadUInt16LittleEndian(bytes.AsSpan(4))!=16))throw new InvalidDataException("The previous quick save needs its matching state format 16 engine.");
   files.Add(name,bytes);
  }
  if(files.Count==0)throw new InvalidDataException("No Redux story saves were found in that installation.");
  string game=Path.Combine(Settings.User,"ContentProfiles",CurrentHash,"Game");Physical(game);
  string target=Path.Combine(game,"saves");
  Physical(target);
  if(Directory.Exists(target)&&Directory.EnumerateFileSystemEntries(target).Any())throw new IOException("This edition already has saves. Import into a fresh dev.3 installation so nothing is overwritten.");
  Directory.CreateDirectory(target);var created=new List<string>();
  try {
   foreach(var file in files){string path=Path.Combine(target,file.Key);using(var output=new FileStream(path,FileMode.CreateNew,FileAccess.Write,FileShare.None)){created.Add(path);output.Write(file.Value);}}
   File.WriteAllText(Path.Combine(game,"redux-story-import.json"),JsonSerializer.Serialize(new{PreviousContentHash=PreviousHash,CurrentContentHash=CurrentHash,Files=files.Select(f=>new{Name=f.Key,Sha256=StoryShuffle.Hash(f.Value)}),OriginalSavesPreserved=true,RandomizerSeedsImported=false},Settings.JsonOptions));
  } catch {foreach(string path in created)File.Delete(path);throw;}
  return files.Count;
 }
}
