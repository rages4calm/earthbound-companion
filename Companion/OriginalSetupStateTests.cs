using System.Text.Json;
namespace EarthBoundCompanion;

static class OriginalSetupStateTests {
 internal static void Run(string legacyPath,string currentPath,string scratch) {
  string output=Path.GetFullPath(scratch);if(Directory.Exists(output))throw new IOException("Use a fresh isolated test directory.");
  byte[] legacy=File.ReadAllBytes(legacyPath),current=File.ReadAllBytes(currentPath);
  if(StoryShuffle.Hash(legacy)!="4e01c943711d32c41e85cb858d9058169e7c8b1739fc7dc0a211e441f9631b9b"||StoryShuffle.Hash(current) is not ("01af4f4b590d9e83937b772399ee60a9181e2384e13c1567c94dfc92101b5549" or "792370574832629c0dc436bbc5b3a3993a8670e7e5fc3e3a5b467791ce514462"))throw new InvalidDataException("Supply the audited legacy and current Original packs.");
  string? previous=Settings.OverrideRoot;var checks=new List<string>();Directory.CreateDirectory(output);
  void Observe(string name,byte[]? pack,bool ready,bool update) {
   Settings.OverrideRoot=Path.Combine(output,name);Directory.CreateDirectory(Settings.BaseGame);
   if(pack!=null)File.WriteAllBytes(Path.Combine(Settings.BaseGame,"assets.pak"),pack);
   if(SetupService.DataReady!=ready||SetupService.OriginalMovementUpdateNeeded!=update)throw new InvalidDataException("Incorrect setup decision: "+name);
   checks.Add(name);
  }
  try {
   Observe("missing-data",null,false,false);
   Observe("legacy-data-needs-rebuild",legacy,true,true);
   Observe("current-data-does-not-rebuild",current,true,false);
   Observe("cold-current-data-does-not-rebuild",current,true,false);
   Observe("truncated-header-needs-rebuild",current[..20],true,true);
   byte[] corrupt=(byte[])current.Clone();corrupt[0]^=1;Observe("corrupt-header-needs-rebuild",corrupt,true,true);
   var(start,_)=StoryShuffle.Range(current,"US/events/bank_c3_scripts_combined.bin");
   corrupt=(byte[])current.Clone();corrupt[start]^=1;Observe("missing-movement-marker-needs-rebuild",corrupt,true,true);
   if(StoryShuffle.HashFile(legacyPath)!=StoryShuffle.Hash(legacy)||StoryShuffle.HashFile(currentPath)!=StoryShuffle.Hash(current))throw new InvalidDataException("A source pack changed.");
   File.WriteAllText(Path.Combine(output,"results.json"),JsonSerializer.Serialize(new{Passed=true,Checks=checks,SourcePacksUnchanged=true,NativeRuntimeChanged=false,FullPlaythroughVerified=false},Settings.JsonOptions));
  }finally{Settings.OverrideRoot=previous;}
 }
}
