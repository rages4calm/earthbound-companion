namespace EarthBoundCompanion;

sealed class SetupForm : Form {
 readonly TextBox rom=new(){ReadOnly=true};readonly CheckBox soundtrack=new(){Text="Install the complete MSU soundtrack (about 1.25 GB)",Checked=true,AutoSize=true};
 readonly ProgressBar bar=new(){Minimum=0,Maximum=100,Style=ProgressBarStyle.Marquee};readonly Label status=Theme.Text("Choose your clean EarthBound (USA) ROM.",10,Theme.Muted);
 readonly Button choose,start,cancel;readonly Button exportReport;SetupDiagnostics? diagnostics;CancellationTokenSource? stop;
 readonly bool redux;
 readonly bool soundtrackOnly;
 readonly bool repairOriginal;
 public bool Completed{get;private set;}
 public SetupForm(bool soundtrackOnly=false,bool reduxDevelopment=false) {
  SuspendLayout();
  AppIcon.Apply(this);
  this.soundtrackOnly=soundtrackOnly;
  redux=reduxDevelopment;
  repairOriginal=!soundtrackOnly&&SetupService.OriginalMovementUpdateNeeded;
  AutoScaleDimensions=new SizeF(96,96);AutoScaleMode=AutoScaleMode.Dpi;
  Text="Set up EarthBound Companion";ClientSize=new Size(680,480);MinimumSize=new Size(540,360);FormBorderStyle=FormBorderStyle.Sizable;MaximizeBox=true;MinimizeBox=false;StartPosition=FormStartPosition.CenterParent;BackColor=Theme.Canvas;ForeColor=Theme.Ink;Font=Theme.Font();
  var panel=new FlowLayoutPanel(){Dock=DockStyle.Fill,AutoScroll=true,FlowDirection=FlowDirection.TopDown,WrapContents=false,Padding=new Padding(28)};Controls.Add(panel);
  var title=Theme.Text(redux?"Build MaternalBound Redux":soundtrackOnly?"Complete the soundtrack":repairOriginal?"Update Original game data":"Bring your own game",22);title.Font=Theme.Font(22,FontStyle.Bold);panel.Controls.Add(title);
  panel.Controls.Add(Theme.Text(redux?"Uses your clean USA ROM to build MaternalBound Redux locally. Original and Redux keep separate saves.":soundtrackOnly?"Companion will verify every MSU track and download only what is missing.":"Your ROM is read once to build the native data files. It is never changed or uploaded.",11,Theme.Muted));
  rom.Width=575;rom.Height=31;rom.BackColor=Theme.Surface;rom.ForeColor=Theme.Ink;rom.Text=SetupService.DataReady&&!redux&&!repairOriginal?"Native game data is ready":"No ROM selected";panel.Controls.Add(rom);
  choose=Theme.Button("Choose EarthBound ROM",Choose);choose.Width=250;choose.Visible=redux||((!SetupService.DataReady||repairOriginal)&&!soundtrackOnly);panel.Controls.Add(choose);
  soundtrack.ForeColor=Theme.Ink;soundtrack.Margin=new Padding(0,8,0,8);soundtrack.Visible=!soundtrackOnly;panel.Controls.Add(soundtrack);
  bar.Width=575;bar.Height=22;bar.Visible=false;panel.Controls.Add(bar);status.Width=575;status.AutoSize=true;status.MinimumSize=new Size(0,48);panel.Controls.Add(status);
  var actions=new FlowLayoutPanel(){Dock=DockStyle.Bottom,AutoSize=false,Height=82,WrapContents=true,Padding=new Padding(28,8,28,12),FlowDirection=FlowDirection.LeftToRight};start=Theme.Button(redux?(ReduxProfileService.UpdateNeeded?"Update Redux game data":"Build MaternalBound Redux"):soundtrackOnly?"Verify / install soundtrack":repairOriginal?"Update game data":"Build my PC edition",Begin,true);cancel=Theme.Button("Cancel",CancelSetup);start.Enabled=!redux&&((SetupService.DataReady&&!repairOriginal)||soundtrackOnly);actions.Controls.Add(start);actions.Controls.Add(cancel);Controls.Add(actions);panel.BringToFront();
  exportReport=Theme.Button("Save error report…",SaveReport);exportReport.Visible=false;panel.Controls.Add(exportReport);
  actions.Layout+=(_,_)=>{int height=actions.GetPreferredSize(new Size(actions.ClientSize.Width,0)).Height;if(actions.Height!=height)actions.Height=height;};
  void Fit(){int width=Math.Max(160,panel.ClientSize.Width-panel.Padding.Horizontal-SystemInformation.VerticalScrollBarWidth-4);foreach(Control c in panel.Controls)ResponsiveLayout.Fit(c,width);}
  panel.SizeChanged+=(_,_)=>Fit();Shown+=(_,_)=>{ResponsiveLayout.KeepOnScreen(this);Fit();};
  ResumeLayout(true);
 }
 void Choose(){using var d=new OpenFileDialog(){Title="Choose your EarthBound (USA) ROM",Filter="SNES ROM (*.sfc;*.smc)|*.sfc;*.smc|All files (*.*)|*.*"};if(d.ShowDialog(this)!=DialogResult.OK)return;rom.Text=d.FileName;start.Enabled=true;}
 async void Begin(){
  if(Completed){Close();return;}
  choose.Enabled=start.Enabled=soundtrack.Enabled=false;bar.Visible=true;bar.Style=ProgressBarStyle.Continuous;stop=new();
  string? path=SetupService.DataReady&&!redux&&!repairOriginal?null:rom.Text;
  diagnostics=new SetupDiagnostics(soundtrackOnly?"Soundtrack":redux?"Redux":"Original",soundtrackOnly?null:path);exportReport.Visible=false;
  bool reporting=true;
  var report=new Progress<SetupProgress>(p=>{if(!reporting||IsDisposed)return;diagnostics.Progress(p.Stage,p.Detail);status.Text=p.Detail;if(p.Total>0){bar.Style=ProgressBarStyle.Continuous;bar.Value=(int)Math.Clamp(p.Done*100/Math.Max(1,p.Total),0,100);}else bar.Style=ProgressBarStyle.Marquee;});
  try {
   var result=soundtrackOnly?await SetupService.InstallAsync(null,true,report,stop.Token):await SetupService.InstallGameAsync(path,soundtrack.Checked,redux,report,stop.Token);
   diagnostics.Finish(warning:result.SoundtrackWarning);exportReport.Visible=result.SoundtrackWarning!=null;
   Completed=true;bar.Style=ProgressBarStyle.Continuous;bar.Value=100;status.ForeColor=result.SoundtrackWarning==null?Theme.Ink:Theme.Gold;
   status.Text=result.SoundtrackWarning??(redux?"MaternalBound Redux is ready to play.":result.MsuTracks>0?$"Ready to play. {result.MsuTracks} soundtrack tracks are verified.":"Ready to play. You can install the MSU soundtrack later from Audio.");
   start.Text="Done";start.Enabled=true;cancel.Visible=false;
  } catch(OperationCanceledException){status.Text="Setup canceled. Completed files were kept, so you can continue later.";start.Enabled=true;choose.Enabled=redux||!SetupService.DataReady||repairOriginal;soundtrack.Enabled=true;}
  catch(Exception e){diagnostics.Finish(e);exportReport.Visible=true;bar.Visible=false;status.Text=e.Message+"\nUse Save error report and send the text file with your bug report.";status.ForeColor=Theme.Error;start.Enabled=true;choose.Enabled=redux||!SetupService.DataReady||repairOriginal;soundtrack.Enabled=true;}
  finally{reporting=false;}
 }
 void SaveReport(){
  if(diagnostics==null)return;
  using var dialog=new SaveFileDialog{Title="Save setup error report",FileName="EarthBound-setup-report.txt",Filter="Text report (*.txt)|*.txt",DefaultExt="txt"};
  if(dialog.ShowDialog(this)!=DialogResult.OK)return;
  try{File.WriteAllText(dialog.FileName,diagnostics.Report);MessageBox.Show(this,"Report saved. Send this text file with your bug report.","Setup report",MessageBoxButtons.OK,MessageBoxIcon.Information);}
  catch(Exception e)when(e is IOException or UnauthorizedAccessException){MessageBox.Show(this,"Could not save the report: "+e.Message,"Setup report",MessageBoxButtons.OK,MessageBoxIcon.Error);}
 }
 void CancelSetup(){if(stop!=null&&!stop.IsCancellationRequested){stop.Cancel();return;}DialogResult=DialogResult.Cancel;Close();}
 protected override void Dispose(bool disposing){if(disposing)stop?.Dispose();base.Dispose(disposing);}
}
