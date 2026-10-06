using System.IO.Compression;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Buffers.Binary;

namespace EarthBoundCompanion;

internal sealed record SaveSnapshot(int Version,string SessionId,string AssetHash,string EngineHash,Dictionary<string,string> Saves);
internal sealed record RestoreResult(int Files,string PreviousBackup);

static class SaveRecovery {
 // Match this native engine's on-disk format exactly. Its CRC polynomial is
 // derived from state_dump.c, rather than assuming the standard ZIP CRC.
 internal static uint Crc(ReadOnlySpan<byte> bytes) {uint crc=0xffffffff;foreach(byte b in bytes){crc^=b;for(int i=0;i<8;i++)crc=(crc>>1)^((crc&1)!=0?ProgressionGuard.SaveStateCrcPolynomial:0);}return crc^0xffffffff;}
 internal static bool ValidQuick(byte[] bytes)=>bytes.Length>=20&&bytes.AsSpan(0,4).SequenceEqual("EBSD"u8)&&BinaryPrimitives.ReadUInt16LittleEndian(bytes.AsSpan(4))==ProgressionGuard.SaveStateVersion&&BinaryPrimitives.ReadUInt32LittleEndian(bytes.AsSpan(16))==bytes.Length-20&&BinaryPrimitives.ReadUInt32LittleEndian(bytes.AsSpan(12))==Crc(bytes.AsSpan(20));
 static bool Same(string a,string b)=>Path.GetFullPath(a).TrimEnd(Path.DirectorySeparatorChar).Equals(Path.GetFullPath(b).TrimEnd(Path.DirectorySeparatorChar),StringComparison.OrdinalIgnoreCase);
 static bool IsSave(string name)=>name=="earthbound.srm"||Regex.IsMatch(name,@"\Aquicksave_[1-5]\.bin\.[01]\z",RegexOptions.CultureInvariant);
 internal static SaveSnapshot Snapshot(string session) {
  string id,assets;
  if(Same(session,Settings.BaseGame)){id="story";assets=Path.Combine(Settings.BaseGame,"assets.pak");}
  else if(Same(Path.GetDirectoryName(Path.GetDirectoryName(Path.GetFullPath(session))!)!,Path.Combine(Settings.User,"ContentProfiles"))) {
   string hash=Path.GetFileName(Path.GetDirectoryName(Path.GetFullPath(session))!);
   if(hash.Length!=64||!hash.All(Uri.IsHexDigit)||!Same(session,Path.Combine(Settings.User,"ContentProfiles",hash,"Game")))
    throw new InvalidDataException("Choose a managed content-profile story save folder.");
   assets=Settings.Load().Pak;
   if(!StoryShuffle.HashFile(assets).Equals(hash,StringComparison.OrdinalIgnoreCase))
    throw new InvalidDataException("Select this content profile before backing up or restoring its story saves.");
   id="content:"+hash.ToLowerInvariant();
  } else {
   var seed=StoryShuffle.Read(Path.GetDirectoryName(Path.GetFullPath(session))!);
   if(!Same(session,seed.Session)||!Same(Path.GetDirectoryName(seed.Folder)!,StoryShuffle.Library))throw new InvalidDataException("Choose a managed story or seed save folder.");
   id=seed.Id;assets=seed.Pak;
  }
  string engine=Path.Combine(Settings.BaseGame,"earthbound.exe");
  var hashes=new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase);
  if(Directory.Exists(Path.Combine(session,"saves")))foreach(string f in Directory.EnumerateFiles(Path.Combine(session,"saves")))if(IsSave(Path.GetFileName(f)))hashes.Add(Path.GetFileName(f),StoryShuffle.HashFile(f));
  return new(1,id,StoryShuffle.HashFile(assets),File.Exists(engine)?StoryShuffle.HashFile(engine):"",hashes);
 }
 internal static RestoreResult Restore(string path,string session,bool phoneOnly) {
  // Read and validate everything before touching the destination. Never use
  // ExtractToDirectory: archive paths cannot dictate filesystem writes.
  var target=Snapshot(session);
  using var zip=ZipFile.OpenRead(path);
  if(zip.Entries.Count>100||zip.Entries.Sum(e=>e.Length)>50_000_000)throw new InvalidDataException("This backup exceeds the supported save archive size.");
  var entries=new Dictionary<string,ZipArchiveEntry>(StringComparer.OrdinalIgnoreCase);
  foreach(var entry in zip.Entries) {
   if(entry.FullName.Contains("..")||entry.FullName.Contains('\\')||entry.FullName.StartsWith('/')||entry.FullName.Contains(':')||!entries.TryAdd(entry.FullName,entry))throw new InvalidDataException("This backup contains invalid or duplicate paths.");
  }
  if(!entries.TryGetValue("save-manifest.json",out var manifest)||manifest.Length>65_536)throw new InvalidDataException("This older backup lacks a verified save manifest. Keep it for manual recovery; use a new Companion backup for guided restore.");
  SaveSnapshot saved;
  using(var reader=new StreamReader(manifest.Open()))saved=JsonSerializer.Deserialize<SaveSnapshot>(reader.ReadToEnd())??throw new InvalidDataException("Missing backup manifest.");
  if(saved.Version!=1||saved.Saves==null||saved.SessionId!=target.SessionId||saved.AssetHash!=target.AssetHash)throw new InvalidDataException("This backup belongs to another adventure or asset pack. Select its matching story/seed before restoring.");
  var files=new Dictionary<string,byte[]>();
  foreach(var (name,hash) in saved.Saves) {
   if(!IsSave(name))throw new InvalidDataException("Invalid save name in backup manifest.");
   if(phoneOnly&&name!="earthbound.srm")continue;
   if(!phoneOnly&&name!="earthbound.srm"&&saved.EngineHash!=target.EngineHash)throw new InvalidDataException("These quick saves use another engine build. Choose phone saves only to restore the normal in-game save.");
   if(!entries.TryGetValue("saves/"+name,out var entry)||entry.Length is <=0 or >4_000_000)throw new InvalidDataException("Missing or oversized save in backup.");
   using var stream=entry.Open();using var buffer=new MemoryStream();stream.CopyTo(buffer);byte[] data=buffer.ToArray();
   if(StoryShuffle.Hash(data)!=hash||name=="earthbound.srm"&&data.Length!=8192)throw new InvalidDataException("A save in this backup is damaged or has the wrong format.");
   if(name!="earthbound.srm"&&!ValidQuick(data))throw new InvalidDataException("A quick save in this backup is incomplete, damaged or uses an unsupported format. Choose phone saves only for recovery.");
   files.Add(name,data);
  }
  if(files.Count==0)throw new InvalidDataException(phoneOnly?"This backup contains no phone save.":"This backup contains no supported saves.");
  string previous=Settings.Backup(true,session),saveDir=Path.Combine(session,"saves");Directory.CreateDirectory(saveDir);
  string staging=Path.Combine(session,".restoring-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(staging);
  var before=new Dictionary<string,byte[]?>();var applied=new List<string>();
  try {
   foreach(var (name,data) in files){File.WriteAllBytes(Path.Combine(staging,name),data);string dest=Path.Combine(saveDir,name);before[name]=File.Exists(dest)?File.ReadAllBytes(dest):null;}
   foreach(string name in files.Keys){File.Move(Path.Combine(staging,name),Path.Combine(saveDir,name),true);applied.Add(name);}
  }catch {
   foreach(string name in applied){string dest=Path.Combine(saveDir,name);if(before[name] is byte[] old)File.WriteAllBytes(dest,old);else File.Delete(dest);}throw;
  }
  // Empty staging directories can be removed without touching any saves.
  if(!Directory.EnumerateFileSystemEntries(staging).Any())Directory.Delete(staging);
  return new(files.Count,previous);
 }
}
