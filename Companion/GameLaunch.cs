using System.Diagnostics;

namespace EarthBoundCompanion;

static class GameLaunch {
 internal static Process Start(Settings settings,bool resume,SeedRecord? seed=null,IReadOnlyList<string>? testArguments=null) {
  if(seed!=null)StoryShuffle.Verify(seed);else settings.ValidatePak();
  Settings.SessionDirectory=seed?.Session;
  try {
   settings.Save();Settings.Backup(true);
   foreach(var marker in new[]{"settings.request","settings.applied"})if(File.Exists(Settings.PathTo(marker)))File.Delete(Settings.PathTo(marker));
   var start=new ProcessStartInfo(HostRuntime.Executable("earthbound")){WorkingDirectory=Settings.Game,UseShellExecute=false,CreateNoWindow=true};
   foreach(var argument in new[]{"--session-dir",Settings.Game,"--assets",seed?.Pak??settings.Pak,"--log-file",Path.Combine(Settings.Game,"game.log")})start.ArgumentList.Add(argument);
   if(ReduxProfileService.AllowDevelopmentLaunch(settings)){
    start.ArgumentList.Add("--allow-redux-development");
    if(settings.OriginalTitleScreen){start.ArgumentList.Add("--original-title-assets");start.ArgumentList.Add(Path.Combine(Settings.BaseGame,"assets.pak"));}
   }
   if(resume)start.ArgumentList.Add("--load-state");
   if(testArguments!=null){foreach(var argument in testArguments)start.ArgumentList.Add(argument);start.Environment["SDL_VIDEODRIVER"]="dummy";start.Environment["SDL_AUDIODRIVER"]="dummy";}
   return Process.Start(start)??throw new IOException("Game did not start.");
  } catch {Settings.SessionDirectory=null;throw;}
 }
}
