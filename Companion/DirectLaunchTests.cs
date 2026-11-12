using System.Diagnostics;
using System.Reflection;
using System.Text.Json;
namespace EarthBoundCompanion;
static class DirectLaunchTests {
 internal static void Run(string originalPack,string reduxPack,string scratch){
  if(Directory.Exists(scratch))throw new IOException("Use a fresh test directory.");
  string previous=Settings.Root;Settings.OverrideRoot=Path.GetFullPath(scratch);
  void Require(bool value,string message){if(!value)throw new InvalidDataException(message);}
  try{
   Directory.CreateDirectory(Settings.BaseGame);
   File.Copy(originalPack,Path.Combine(Settings.BaseGame,"assets.pak"));
   foreach(var name in new[]{"earthbound.exe","SDL2.dll"})File.Copy(Path.Combine(previous,"Game",name),Path.Combine(Settings.BaseGame,name));
   Directory.CreateDirectory(ReduxProfileService.DirectoryPath);File.Copy(reduxPack,ReduxProfileService.Pack);
   File.WriteAllText(Path.Combine(ReduxProfileService.DirectoryPath,"profile.json"),JsonSerializer.Serialize(new{contentId=ReduxProfileService.ContentId,assetPackSha256=StoryShuffle.HashFile(reduxPack)}));
   new Settings{HqAudio=false,Fullscreen=false}.Save();var sessions=new List<string>();
   foreach(bool redux in new[]{false,true}){
    using var form=new MainForm(Array.Empty<string>());using var context=new DirectGameContext(form);
    form.LaunchDirect(redux,["--headless","--skip-intro","--frames","300000"]);
    var process=(Process)typeof(MainForm).GetField("game",BindingFlags.NonPublic|BindingFlags.Instance)!.GetValue(form)!;
    string session=Settings.Game;sessions.Add(session);Require(!form.Visible,"Direct launch displayed its window.");
    var watch=Stopwatch.StartNew();bool requested=false,checkedSettings=false,timedOut=false;
    using var timer=new System.Windows.Forms.Timer{Interval=50};
    timer.Tick+=(_,_)=>{
     if(!requested){File.WriteAllText(Settings.PathTo("settings.request"),"");requested=true;}
     if(form.Visible&&!checkedSettings){
      form.Close();checkedSettings=!form.Visible&&!process.HasExited;
      if(!process.HasExited)process.Kill();
     }
     if(watch.ElapsedMilliseconds>15000){timedOut=true;timer.Stop();if(!process.HasExited)process.Kill();context.ExitThread();}
    };
    timer.Start();Application.Run(context);timer.Stop();
    Require(!timedOut&&checkedSettings,"Settings handoff/close or game-exit lifetime failed.");
    Require(File.Exists(Path.Combine(session,"game.log")),"Native launch did not write its session log.");
   }
   Require(sessions[0]!=sessions[1],"Original and Redux shared a save directory.");
   File.WriteAllText(Path.Combine(scratch,"results.json"),JsonSerializer.Serialize(new{Passed=true,Checks=new[]{"Hidden startup in both modes","Separate existing content sessions","Actual native child process","Settings request opens window","Closing settings resumes/hides without quitting game","Context exits when child exits"}},Settings.JsonOptions));
  }finally{Settings.OverrideRoot=previous;Settings.SessionDirectory=null;new Settings().ConfigureContentSession();}
 }
}
