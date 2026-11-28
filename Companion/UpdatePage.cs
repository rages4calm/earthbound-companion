// SPDX-License-Identifier: GPL-3.0-or-later
namespace EarthBoundCompanion;
sealed partial class MainForm {
 CancellationTokenSource? updateOperation;
 bool updateHandoff;
 Button? updateNotice;
 UpdateCheck? availableUpdate;
 void InitializeUpdates(string[] args) {
  updateNotice=Theme.Button("Updates",()=>ShowPage("Updates"));updateNotice.AutoSize=false;updateNotice.MinimumSize=new Size(166,44);updateNotice.Size=new Size(166,44);updateNotice.Margin=new Padding(0,0,0,8);updateNotice.AccessibleName="Check for updates";
  nav.Controls.Add(updateNotice);nav.Controls.SetChildIndex(updateNotice,3);
  Shown+=async(_,_)=>{
   if(captureMode||args.Contains("--layout-check"))return;
   var message=UpdateService.FinishPending(UpdateService.InstallDirectory);if(message!=null)Notify(message);
   if(!UpdatePreferences.CheckOnStart)return;
   try{availableUpdate=await UpdateService.CheckAsync(UpdateService.InstallDirectory);if(availableUpdate.IsNewer&&!IsDisposed){updateNotice.Text="Update available";updateNotice.ForeColor=Theme.Gold;}}
   catch(Exception){ /* Offline/rate-limited checks never interrupt play. */ }
  };
  FormClosing+=(_,e)=>{if(updateOperation!=null&&!updateHandoff){updateOperation.Cancel();e.Cancel=true;Notify("Cancelling the update download…");}};
 }
 void UpdatesPage() {
  Header("Updates","Get the latest EarthBound Companion build without downloading and extracting it by hand.");
  page.Controls.Add(Theme.Text("Installed: "+UpdateService.CurrentVersion(UpdateService.InstallDirectory),13,Theme.Gold));
  page.Controls.Add(Theme.Text("Updates keep this folder in place, so your Steam shortcuts keep working. Your Original and Redux data, saves, seeds, settings and soundtrack stay here.",11,Theme.Muted));
  Check("Check when the launcher opens","Checks GitHub quietly. Updates only install when you press Install update.",UpdatePreferences.CheckOnStart,v=>UpdatePreferences.CheckOnStart=v);
  var summary=Theme.Text("Check for a newer release.",12);page.Controls.Add(summary);
  var notes=new TextBox{Multiline=true,ReadOnly=true,ScrollBars=ScrollBars.Vertical,WordWrap=true,Height=190,Width=680,BackColor=Theme.Surface,ForeColor=Theme.Ink,BorderStyle=BorderStyle.FixedSingle,Font=Theme.Font(10),AccessibleName="Release notes"};page.Controls.Add(notes);
  var progress=new ProgressBar{Height=22,Width=680,AccessibleName="Update progress",Visible=false};page.Controls.Add(progress);
  Button? check=null,install=null,cancel=null;
  void ShowResult(){
   summary.Text=availableUpdate?.Latest is {} latest?(availableUpdate.IsNewer?$"Available: {latest.Version} · {latest.Zip.Size/1048576.0:0.0} MB":$"You have the latest release ({availableUpdate.Current})."):"No downloadable Windows release was found.";
   notes.Text=availableUpdate?.Latest?.Notes??"";install!.Enabled=availableUpdate?.IsNewer==true;install.BackColor=install.Enabled?Theme.Gold:Theme.Surface;
  }
  check=Theme.Button("Check again",async()=>{
   if(updateOperation!=null)return;updateOperation=new();check!.Enabled=false;install!.Enabled=false;cancel!.Enabled=true;progress.Visible=true;progress.Style=ProgressBarStyle.Marquee;
   try{availableUpdate=await UpdateService.CheckAsync(UpdateService.InstallDirectory,cancel:updateOperation.Token);ShowResult();Notify("Update check finished.");}
   catch(OperationCanceledException){Notify("Update check cancelled.");}
   catch(Exception e){Notify(e.Message,true);}
   finally{updateOperation.Dispose();updateOperation=null;if(!check.IsDisposed){check.Enabled=true;cancel!.Enabled=false;progress.Visible=false;}}
  });
  install=Theme.Button("Install update",async()=>{
   if(updateOperation!=null||availableUpdate?.IsNewer!=true||availableUpdate.Latest is not {} latest)return;
   if(Running||generating){Notify("Close the game and finish seed generation before updating.",true);return;}
   updateOperation=new();check.Enabled=install!.Enabled=false;cancel!.Enabled=true;progress.Visible=true;progress.Style=ProgressBarStyle.Blocks;
   try {
    Apply();
    var report=new Progress<UpdateProgress>(v=>{if(!progress.IsDisposed){progress.Value=v.Total>0?(int)Math.Clamp(v.Done*100/v.Total,0,100):0;Notify(v.Phase+(v.Phase=="Downloading"?$" · {v.Done/1048576.0:0.0} MB":"…"));}});
    string plan=await UpdateService.StageAsync(UpdateService.InstallDirectory,latest,report,updateOperation.Token);
    using var helper=UpdateService.StartHelper(plan);updateHandoff=true;Close();Application.Exit();
   }catch(OperationCanceledException){Notify("Update cancelled. Your installation is unchanged.");}
   catch(Exception e){Notify(e.Message,true);}
   finally{updateOperation.Dispose();updateOperation=null;if(!check.IsDisposed){check.Enabled=true;cancel!.Enabled=false;install.Enabled=availableUpdate?.IsNewer==true;progress.Visible=false;}}
  },true);
  install.Enabled=false;install.BackColor=Theme.Surface;
  cancel=Theme.Button("Cancel download",()=>updateOperation?.Cancel());cancel.Enabled=false;
  Actions(check,install,cancel);
  if(availableUpdate!=null)ShowResult();
 }
}
