using System.Buffers.Binary;
using System.Diagnostics;
using System.Text.Json;

namespace EarthBoundCompanion;

// Developer-only actual checkpoint test. All mutation occurs in a fresh folder;
// the supplied pack and checkpoint are read-only inputs.
static class CheckpointRecoveryTests {
 internal static void Run(string assetPath,string checkpointPath,string directory) {
  directory=Path.GetFullPath(directory);
  if(Directory.Exists(directory))throw new InvalidDataException("Choose a fresh checkpoint-test directory.");
  assetPath=Path.GetFullPath(assetPath);checkpointPath=Path.GetFullPath(checkpointPath);
  byte[] pack=File.ReadAllBytes(assetPath),checkpoint=File.ReadAllBytes(checkpointPath);
  string packHash=StoryShuffle.Hash(pack),checkpointHash=StoryShuffle.Hash(checkpoint);
  var policy=ProgressionGuard.CheckBase(pack);
  if(checkpoint.Length<20||!checkpoint.AsSpan(0,4).SequenceEqual("EBSD"u8)||BinaryPrimitives.ReadUInt16LittleEndian(checkpoint.AsSpan(4))!=16)
   throw new InvalidDataException("Supply an actual native format-16 checkpoint.");
  string installed=Settings.BaseGame;
  Directory.CreateDirectory(directory);Settings.OverrideRoot=directory;Settings.SessionDirectory=null;
  try {
   string session=Settings.BaseGame;Directory.CreateDirectory(session);
   File.WriteAllBytes(Path.Combine(session,"assets.pak"),pack);
   foreach(string name in new[]{"earthbound.exe","SDL2.dll"})File.Copy(Path.Combine(installed,name),Path.Combine(session,name));
   string saves=Path.Combine(session,"saves");Directory.CreateDirectory(saves);
   string quick=Path.Combine(saves,"quicksave_1.bin.0");File.WriteAllBytes(quick,checkpoint);
   string backup=Settings.Backup(true,session);
   File.WriteAllBytes(quick,new byte[checkpoint.Length]);
   var restored=SaveRecovery.Restore(backup,session,false);
   if(restored.Files!=1||!File.ReadAllBytes(quick).SequenceEqual(checkpoint)||!File.Exists(restored.PreviousBackup))
    throw new InvalidDataException("Actual checkpoint was not restored exactly.");
   // The former registry version must be refused even when its payload CRC is
   // valid. Use a private edited copy, never the supplied owner's checkpoint.
   byte[] obsolete=(byte[])checkpoint.Clone();BinaryPrimitives.WriteUInt16LittleEndian(obsolete.AsSpan(4),12);
   File.WriteAllBytes(quick,obsolete);string oldBackup=Settings.Backup(true,session);
   File.WriteAllBytes(quick,checkpoint);bool refused=false;
   try{SaveRecovery.Restore(oldBackup,session,false);}catch(InvalidDataException){refused=true;}
   if(!refused||!File.ReadAllBytes(quick).SequenceEqual(checkpoint))throw new InvalidDataException("Obsolete format accepted or destination changed.");
   var start=new ProcessStartInfo(Path.Combine(session,"earthbound.exe")){UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true};
   foreach(string arg in new[]{"--assets",Path.Combine(session,"assets.pak"),"--session-dir",session,"--allow-redux-development","--headless","--load-state","--frames","100"})start.ArgumentList.Add(arg);
   start.Environment["SDL_VIDEODRIVER"]="dummy";start.Environment["SDL_AUDIODRIVER"]="dummy";
   using var process=Process.Start(start)??throw new IOException("Native checkpoint reader did not start.");
   var stdout=process.StandardOutput.ReadToEndAsync();var stderr=process.StandardError.ReadToEndAsync();
   if(!process.WaitForExit(30_000)){process.Kill();throw new IOException("Native checkpoint test timed out.");}
   string log=stdout.GetAwaiter().GetResult()+stderr.GetAwaiter().GetResult();File.WriteAllText(Path.Combine(directory,"native.log"),log);
   if(process.ExitCode!=0||!log.Contains("savestate: loaded slot"))throw new InvalidDataException("Native engine failed to load the restored checkpoint.");
   if(StoryShuffle.HashFile(assetPath)!=packHash||StoryShuffle.HashFile(checkpointPath)!=checkpointHash)throw new IOException("Read-only checkpoint inputs changed.");
   File.WriteAllText(Path.Combine(directory,"results.json"),JsonSerializer.Serialize(new {Passed=true,policy.ContentId,PackSha256=packHash,CheckpointSha256=checkpointHash,NativeExeSha256=StoryShuffle.HashFile(Path.Combine(session,"earthbound.exe")),ActualCheckpointVersion=16,ObsoleteVersion12Rejected=true,ExactBytesRestored=true,NativeCheckpointLoaded=true,InputsUnchanged=true,FullPlaythroughVerified=false},Settings.JsonOptions));
  }finally{Settings.OverrideRoot=null;Settings.SessionDirectory=null;}
 }
}
