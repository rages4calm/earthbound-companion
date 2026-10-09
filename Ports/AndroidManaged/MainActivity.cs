// SPDX-License-Identifier: GPL-3.0-or-later
using global::Android.App;
using global::Android.Content;
using global::Android.Content.PM;
using Avalonia;
using Avalonia.Android;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Themes.Fluent;
using EarthBoundCompanion;

namespace EarthBoundCompanion.Android;
[Activity(Name="org.earthbound.companion.ManagedLauncher",Label="EarthBound Companion Preview",MainLauncher=true,Exported=true,ConfigurationChanges=ConfigChanges.Orientation|ConfigChanges.ScreenSize|ConfigChanges.UiMode,Theme="@android:style/Theme.Material.NoActionBar")]
public sealed class MainActivity : AvaloniaMainActivity<MobileApp> {
 internal static MainActivity? Current;
 TaskCompletionSource? gameClosed;
 protected override void OnCreate(global::Android.OS.Bundle? state){Current=this;Settings.OverrideRoot=Path.Combine(FilesDir!.AbsolutePath,"CompanionPreview");HostRuntime.NativeLibraryDirectory=ApplicationInfo!.NativeLibraryDir;base.OnCreate(state);}
 protected override AppBuilder CustomizeAppBuilder(AppBuilder builder)=>base.CustomizeAppBuilder(builder).WithInterFont();
 protected override void OnResume(){base.OnResume();if(gameClosed!=null&&File.Exists(Settings.PathTo("settings.request")))return;gameClosed?.TrySetResult();gameClosed=null;}
 internal void ReturnToGame(){if(gameClosed==null)return;var intent=new Intent();intent.SetClassName(this,"org.earthbound.companion.GameActivity");intent.AddFlags(ActivityFlags.ReorderToFront);StartActivity(intent);}
 internal Task Launch(Settings settings,bool resume,SeedRecord? seed){
  if(seed!=null)StoryShuffle.Verify(seed);else settings.ValidatePak();Settings.SessionDirectory=seed?.Session;
  try {
   settings.ShaderPreset="";settings.Save();Settings.Backup(true);
   foreach(var marker in new[]{"settings.request","settings.applied"})File.Delete(Settings.PathTo(marker));
   var args=new List<string>{"--session-dir",Settings.Game,"--assets",seed?.Pak??settings.Pak,"--log-file",Path.Combine(Settings.Game,"game.log")};
   if(ReduxProfileService.AllowDevelopmentLaunch(settings)){args.Add("--allow-redux-development");if(settings.OriginalTitleScreen){args.Add("--original-title-assets");args.Add(Path.Combine(Settings.BaseGame,"assets.pak"));}}
   if(resume)args.Add("--load-state");
   var intent=new Intent();intent.SetClassName(this,"org.earthbound.companion.GameActivity");intent.PutExtra("arguments",args.ToArray());gameClosed=new(TaskCreationOptions.RunContinuationsAsynchronously);StartActivity(intent);return gameClosed.Task;
  }catch{Settings.SessionDirectory=null;throw;}
 }
}
public sealed class MobileApp : Application {
 public override void Initialize(){RequestedThemeVariant=Avalonia.Styling.ThemeVariant.Dark;Styles.Add(new FluentTheme());}
 public override void OnFrameworkInitializationCompleted(){if(ApplicationLifetime is ISingleViewApplicationLifetime single)single.MainView=new MainView((settings,resume,seed)=>MainActivity.Current!.Launch(settings,resume,seed),()=>MainActivity.Current!.ReturnToGame());base.OnFrameworkInitializationCompleted();}
}
