// SPDX-License-Identifier: GPL-3.0-or-later
using System.IO.Compression;
using System.Formats.Tar;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using EarthBoundCompanion;
static class UpdateTests {
 static int checks;
 static void Check(bool value,string message){checks++;if(!value)throw new Exception("Updater: "+message);}
 static void Refused(Action action,string message){try{action();}catch(IOException){checks++;return;}throw new Exception("Updater accepted "+message);}
 static string Hash(string file)=>Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(file)));
 public static async Task Run(string parent) {
  string root=Path.Combine(parent,"updater");Directory.CreateDirectory(root);
  Check(ReleaseVersion.Parse("1.0.28")>ReleaseVersion.Parse("1.0.27"),"stable ordering");
  Check(ReleaseVersion.Parse("0.5.0-ports-preview.38")>ReleaseVersion.Parse("0.5.0-ports-preview.9"),"numeric prerelease ordering");
  Check(!ReleaseVersion.TryParse("1.0.0-preview.01",out _),"invalid semver");
  string Feed(params (string Tag,string Name,bool Draft,bool Preview)[] releases)=>JsonSerializer.Serialize(releases.Select(r=>new{tag_name=r.Tag,draft=r.Draft,prerelease=r.Preview,body="# Fixed\n**NPCs**",assets=new[]{new{name=r.Name,browser_download_url="https://github.com/rages4calm/earthbound-companion/releases/download/"+r.Tag+"/"+r.Name,size=12,digest="sha256:"+new string('a',64)}}}));
  var feed=Feed(("v1.0.28","EarthBound-Companion-Windows-v1.0.28.zip",false,false),("v1.0.29","EarthBound-Companion-Windows-v1.0.29.zip",true,false),("v9.0.0-beta.1","EarthBound-Companion-Windows-v9.0.0-beta.1.zip",false,true));
  Check(UpdateService.PickLatest(feed,"win-x64")!.Version.ToString()=="1.0.28","draft/prerelease excluded from Windows");
  foreach(string platform in new[]{"linux-x64","osx-arm64","osx-x64","android-arm64","android-x64"}) {
   string name=$"EarthBound-Companion-{platform}-preview."+(platform.StartsWith("android-")?"apk":"tar.gz");
   Check(UpdateService.PickLatest(Feed(("v0.5.0-ports-preview.38",name,false,true)),platform)!.Zip.Name==name,"platform selection "+platform);
  }
  Refused(()=>UpdateService.RequireAllowed(new Uri("http://github.com/bad")),"plain HTTP");
  Refused(()=>UpdateService.RequireAllowed(new Uri("https://github.com.evil.example/file")),"lookalike host");
  var win=new Dictionary<string,string>{{"EarthBound Companion.exe","new launcher"},{"Game/earthbound.exe","new engine"},{"docs/notes.txt","notes"}};
  string Zip(string name,Dictionary<string,string> files){string path=Path.Combine(root,name);using var z=ZipFile.Open(path,ZipArchiveMode.Create);foreach(var f in files){var e=z.CreateEntry("EarthBound Companion/"+f.Key);using var w=new StreamWriter(e.Open());w.Write(f.Value);}return path;}
  string good=Zip("good.zip",win);
  Check(UpdateService.ExtractPackage(good,Path.Combine(root,"extract"),"win-x64").Count==3,"valid ZIP");
  foreach(string bad in new[]{"../escape","Game/../../../escape","UserData/settings.json","Game/assets.pak","Game/saves/earthbound.srm"}) {
   string path=Zip("bad-"+checks+".zip",new(win){{bad,"bad"}});
   Refused(()=>UpdateService.ExtractPackage(path,Path.Combine(root,"bad-extract-"+checks),"win-x64"),bad);
  }
  foreach(string platform in new[]{"linux-x64","osx-arm64","osx-x64"}) {
   string path=Path.Combine(root,platform+".tar.gz"),prefix=platform.StartsWith("osx-")?"./EarthBound Companion Preview.app/":"./",bin=platform.StartsWith("osx-")?"Contents/MacOS/":"";
   using(var file=File.Create(path))using(var gzip=new GZipStream(file,CompressionLevel.Fastest))using(var tar=new TarWriter(gzip))foreach(string name in new[]{bin+"EarthBoundCompanion.Portable",bin+"Game/earthbound"}) {
    using var data=new MemoryStream(Encoding.UTF8.GetBytes(name));var e=new PaxTarEntry(TarEntryType.RegularFile,prefix+name){DataStream=data,Mode=(UnixFileMode)0x1ed};tar.WriteEntry(e);
   }
   Check(UpdateService.ExtractPackage(path,Path.Combine(root,platform),platform).Count==2,"tar layout "+platform);
  }
  string install=Path.Combine(root,"installed");Directory.CreateDirectory(Path.Combine(install,Path.GetDirectoryName(UpdateService.EngineRelative)!));
  Directory.CreateDirectory(Path.GetDirectoryName(Path.Combine(install,UpdateService.LauncherRelative))!);
  File.WriteAllText(Path.Combine(install,UpdateService.LauncherRelative),"old launcher");File.WriteAllText(Path.Combine(install,UpdateService.EngineRelative),"old engine");
  foreach(string name in new[]{"Game/assets.pak","Game/saves/earthbound.srm","Profiles/Redux/assets.pak","UserData/settings.json","UserData/Seeds/test/seed.json","msu/music.pcm"}){Directory.CreateDirectory(Path.GetDirectoryName(Path.Combine(install,name))!);File.WriteAllText(Path.Combine(install,name),"private:"+name);}
  var protectedFiles=Directory.GetFiles(install,"*",SearchOption.AllDirectories).ToDictionary(f=>f,Hash);
  string Work()=>Path.Combine(root,".installed-eb-update-"+Guid.NewGuid().ToString("N"));
  (string Work,UpdateService.UpdatePlan Plan) MakePlan() {
   string work=Work();var files=new List<UpdateService.PackageFile>();
   foreach(var f in new Dictionary<string,string>{{UpdateService.LauncherRelative,"new launcher"},{UpdateService.EngineRelative,"new engine"},{"new-doc.txt","new file"}}){string path=Path.Combine(work,"new",f.Key);Directory.CreateDirectory(Path.GetDirectoryName(path)!);File.WriteAllText(path,f.Value);files.Add(new(f.Key,Hash(path)));}
   return(work,new(install,UpdateService.Platform,"1.0.28",0,files));
  }
  var broken=MakePlan();Refused(()=>UpdateService.ApplyPlan(broken.Plan,broken.Work,step=>{if(step==UpdateService.EngineRelative)throw new IOException("Injected replacement failure");}),"replacement failure");
  Check(protectedFiles.All(f=>Hash(f.Key)==f.Value),"rollback preserves every original byte");Check(!File.Exists(Path.Combine(install,"new-doc.txt")),"rollback removes newly created files");
  var tampered=MakePlan();File.AppendAllText(Path.Combine(tampered.Work,"new",UpdateService.EngineRelative),"tampered");Refused(()=>UpdateService.ApplyPlan(tampered.Plan,tampered.Work),"tampered staging");
  var unsafePlan=MakePlan();Refused(()=>UpdateService.ApplyPlan(unsafePlan.Plan with {Files=[..unsafePlan.Plan.Files,new("../outside","00")]},unsafePlan.Work),"unsafe plan");
  var ready=MakePlan();UpdateService.ApplyPlan(ready.Plan,ready.Work);
  Check(File.ReadAllText(Path.Combine(install,UpdateService.EngineRelative))=="new engine","new runtime installed");
  Check(protectedFiles.Where(f=>f.Key!=Path.GetFullPath(Path.Combine(install,UpdateService.EngineRelative))&&f.Key!=Path.GetFullPath(Path.Combine(install,UpdateService.LauncherRelative))).All(f=>Hash(f.Key)==f.Value),"saves/packs/seeds/settings/MSU untouched");
  Check(UpdateService.FinishPending(install)!=null&&!Directory.Exists(ready.Work),"completed staging cleanup");
  var bytes=Encoding.UTF8.GetBytes("download fixture");string digest=Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
  using var client=new HttpClient(new FixtureHttp(bytes));
  var asset=new UpdateAsset("test.zip",new Uri("https://github.com/test.zip"),bytes.Length,digest);
  var release=new UpdateRelease(ReleaseVersion.Parse("1.0.28"),"v1.0.28","test","",asset,null,null);
  string download=Path.Combine(root,"download.zip");await UpdateService.DownloadAsync(release,download,client:client);Check(Hash(download).Equals(digest,StringComparison.OrdinalIgnoreCase),"download SHA256 verified");
  try{await UpdateService.DownloadAsync(release with {Zip=asset with {Sha256=new string('f',64)}},Path.Combine(root,"mismatch.zip"),client:client);throw new Exception("digest mismatch accepted");}catch(UpdateException){checks++;}
  Check(!File.Exists(Path.Combine(root,"mismatch.zip"))&&!File.Exists(Path.Combine(root,"mismatch.zip.partial")),"mismatched download removed");
  Console.WriteLine($"Updater: {checks} checks passed (feed, archives, digest, preservation, rollback, cleanup).");
 }
 sealed class FixtureHttp(byte[] bytes):HttpMessageHandler {
  protected override Task<HttpResponseMessage> SendAsync(HttpRequestMessage request,CancellationToken cancel)=>Task.FromResult(new HttpResponseMessage(HttpStatusCode.OK){RequestMessage=request,Content=new ByteArrayContent(bytes)});
 }
}
