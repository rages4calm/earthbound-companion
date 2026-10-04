using System.Diagnostics;

namespace EarthBoundCompanion;

static class NativeRecoveryTests {
 public static void Run(string directory) {
  directory=Path.GetFullPath(directory);string actualRoot=Settings.Root;
  string seedPak=File.ReadAllText(Path.Combine(directory,"native-seed-path.txt")),session=File.ReadAllText(Path.Combine(directory,"native-session-path.txt"));
  string fixture=Path.Combine(directory,"library-fixture-v2");
  if(!Path.GetFullPath(session).StartsWith(Path.GetFullPath(Path.Combine(fixture,"UserData","Seeds"))+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("Native recovery tests require the isolated version 2 seed fixture.");
  var before=new Dictionary<string,string>();foreach(string f in Directory.EnumerateFiles(Path.Combine(actualRoot,"Game","saves")))before[f]=StoryShuffle.HashFile(f);
  Settings.OverrideRoot=fixture;
  try {
   var seed=StoryShuffle.Read(Path.GetDirectoryName(session)!);StoryShuffle.Verify(seed);
   foreach(string file in new[]{"earthbound.exe","SDL2.dll"})File.Copy(Path.Combine(actualRoot,"Game",file),Path.Combine(Settings.BaseGame,file),true);
   string savedSettings=StoryShuffle.HashFile(Path.Combine(session,"earthbound.ini"));
   var original=SaveRecovery.Snapshot(session);string backup=Settings.Backup(true,session);
   // Damage the real native-generated quick-save slot in the isolated fixture.
   // The backup's native header/CRC is checked before it is restored.
   string quick=Path.Combine(session,"saves","quicksave_1.bin.0");if(!File.Exists(quick))quick=Path.Combine(session,"saves","quicksave_1.bin.1");
   byte[] native=File.ReadAllBytes(quick);File.WriteAllBytes(quick,new byte[native.Length]);
   var restored=SaveRecovery.Restore(backup,session,false);var after=SaveRecovery.Snapshot(session);
   if(original.Saves.Count!=after.Saves.Count||original.Saves.Any(p=>after.Saves.GetValueOrDefault(p.Key)!=p.Value)||!File.Exists(restored.PreviousBackup)||StoryShuffle.HashFile(Path.Combine(session,"earthbound.ini"))!=savedSettings)throw new Exception("Native recovery did not restore the exact save set or changed settings.");
   var start=new ProcessStartInfo(Path.Combine(Settings.BaseGame,"earthbound.exe")){UseShellExecute=false,CreateNoWindow=true,RedirectStandardError=true,RedirectStandardOutput=true};
   foreach(string arg in new[]{"--session-dir",session,"--assets",seedPak,"--windowed","--load-state","--frames","100","--capture-state","20"})start.ArgumentList.Add(arg);
   start.Environment["SDL_VIDEODRIVER"]="dummy";start.Environment["SDL_AUDIODRIVER"]="dummy";
   using var process=Process.Start(start)??throw new IOException("Native recovery game test did not start.");
   var stdout=process.StandardOutput.ReadToEndAsync();var stderr=process.StandardError.ReadToEndAsync();
   if(!process.WaitForExit(30_000)){process.Kill();throw new Exception("Native recovery game test timed out.");}
   string log=stdout.GetAwaiter().GetResult()+stderr.GetAwaiter().GetResult();File.WriteAllText(Path.Combine(directory,"native-recovery.log"),log);
   if(process.ExitCode!=0||!log.Contains("savestate: loaded slot")||!log.Contains("party=1")||!log.Contains("level=1 HP=30"))throw new Exception("The native engine could not resume the restored checkpoint.");
   foreach(var (file,hash) in before)if(StoryShuffle.HashFile(file)!=hash)throw new Exception("Installed story save changed during isolated recovery tests.");
   File.WriteAllText(Path.Combine(directory,"native-recovery-tests.txt"),"PASS: verified backup restores a damaged native checkpoint byte-for-byte; engine loads the restored state and resumes Ness at level 1 / 30 HP; settings and installed story saves unchanged.\n");
  }finally{Settings.OverrideRoot=null;Settings.SessionDirectory=null;}
 }
}
