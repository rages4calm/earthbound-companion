// SPDX-License-Identifier: GPL-3.0-or-later
using System.Diagnostics;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Layout;
namespace EarthBoundCompanion;
public sealed partial class MainView {
 bool updateHandoff;
 UpdateCheck? updateCheck;
 StackPanel Updates() {
  var panel=Page();
  panel.Children.Add(Text("Installed: "+UpdateService.CurrentVersion(UpdateService.InstallDirectory)));
  panel.Children.Add(Text(mobileLaunch!=null
   ?"Check for a newer APK for this device. Android will ask you to install it over the current app; keep the app installed to retain its saves and game data."
   :"Updates replace this installation in place. Game data and saves stay in your existing preview data folder; Steam shortcuts keep the same path."));
  Check(panel,"Check for updates when the launcher opens",()=>UpdatePreferences.CheckOnStart,v=>UpdatePreferences.CheckOnStart=v);
  var summary=Text("Check for a newer release.");panel.Children.Add(summary);
  var notes=new TextBox{IsReadOnly=true,AcceptsReturn=true,TextWrapping=Avalonia.Media.TextWrapping.Wrap,MinHeight=180,MaxHeight=280,Watermark="Release notes"};panel.Children.Add(notes);
  var progress=new ProgressBar{Minimum=0,Maximum=100,IsVisible=false,Height=18};panel.Children.Add(progress);
  Button? install=null;
  void ShowResult(){summary.Text=updateCheck?.Latest is {} latest?(updateCheck.IsNewer?$"Available: {latest.Version} · {latest.Zip.Size/1048576.0:0.0} MB":$"You have the latest release ({updateCheck.Current})."):"No release package was found for this device.";notes.Text=updateCheck?.Latest?.Notes??"";install!.IsEnabled=updateCheck?.IsNewer==true;}
  panel.Children.Add(Action("Check for updates",async()=>{
   progress.IsVisible=true;progress.IsIndeterminate=true;
   try{updateCheck=await UpdateService.CheckAsync(UpdateService.InstallDirectory);ShowResult();status.Text="Update check finished.";}
   finally{progress.IsVisible=false;progress.IsIndeterminate=false;}
  }));
  install=Action(mobileLaunch!=null?"Download Android update":"Install update",async()=>{
   if(updateCheck?.IsNewer!=true||updateCheck.Latest is not {} latest)return;
   if(gameRunning)throw new IOException("Close the game before updating.");
   Capture();settings.Save();
   if(mobileLaunch!=null){
    UpdateService.RequireAllowed(latest.Zip.Url);
    if(!await TopLevel.GetTopLevel(this)!.Launcher.LaunchUriAsync(latest.Zip.Url))throw new IOException("Android could not open the download link. Get the matching APK from GitHub releases.");
    status.Text="Download "+latest.Zip.Name+", then open it to update the existing app. Do not uninstall first.";return;
   }
   progress.IsVisible=true;
   try {
    var report=new Progress<UpdateProgress>(v=>{progress.Value=v.Total>0?Math.Clamp(v.Done*100.0/v.Total,0,100):0;status.Text=v.Phase+(v.Phase=="Downloading"?$" · {v.Done/1048576.0:0.0} MB":"…");});
    string plan=await UpdateService.StageAsync(UpdateService.InstallDirectory,latest,report);
    using var helper=UpdateService.StartHelper(plan);updateHandoff=true;
    if(Application.Current?.ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)desktop.Shutdown();
   }finally{progress.IsVisible=false;}
  });
  install.IsEnabled=false;panel.Children.Add(install);
  AttachedToVisualTree+=async(_,_)=>{
   if(mobileLaunch==null){var message=UpdateService.FinishPending(UpdateService.InstallDirectory);if(message!=null)status.Text=message;}
   if(!UpdatePreferences.CheckOnStart)return;
   try{updateCheck=await UpdateService.CheckAsync(UpdateService.InstallDirectory);ShowResult();if(updateCheck.IsNewer)status.Text="A new release is available. Open Updates to read the changes and install it.";}catch(Exception){ }
  };
  return panel;
 }
}
