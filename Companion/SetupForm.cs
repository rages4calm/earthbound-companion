namespace EarthBoundCompanion;

sealed class SetupForm : Form {
 readonly TextBox rom=new(){ReadOnly=true};readonly CheckBox soundtrack=new(){Text="Install the complete MSU soundtrack (about 1.25 GB)",Checked=true,AutoSize=true};
 readonly ProgressBar bar=new(){Minimum=0,Maximum=100,Style=ProgressBarStyle.Marquee};readonly Label status=Theme.Text("Choose your clean EarthBound (USA) ROM.",10,Theme.Muted);
 readonly Button choose,start,cancel;CancellationTokenSource? stop;
 readonly bool redux;
 public bool Completed{get;private set;}
 public SetupForm(bool soundtrackOnly=false,bool reduxDevelopment=false) {
  AppIcon.Apply(this);
  redux=reduxDevelopment;
  Text="Set up EarthBound Companion";ClientSize=new Size(650,410);MinimumSize=MaximumSize=Size;FormBorderStyle=FormBorderStyle.FixedDialog;MaximizeBox=false;MinimizeBox=false;StartPosition=FormStartPosition.CenterParent;BackColor=Theme.Canvas;ForeColor=Theme.Ink;Font=Theme.Font();
  var panel=new FlowLayoutPanel(){Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,WrapContents=false,Padding=new Padding(28)};Controls.Add(panel);
  var title=Theme.Text(redux?"Build the Redux test edition":soundtrackOnly?"Complete the soundtrack":"Bring your own game",22);title.Font=Theme.Font(22,FontStyle.Bold);panel.Controls.Add(title);
  panel.Controls.Add(Theme.Text(redux?"Uses your clean USA ROM. This development edition has separate saves; a full playthrough is still unverified.":soundtrackOnly?"Companion will verify every MSU track and download only what is missing.":"Your ROM is read once to build the native data files. It is never changed, copied or uploaded.",11,Theme.Muted));
  rom.Width=575;rom.Height=31;rom.BackColor=Theme.Surface;rom.ForeColor=Theme.Ink;rom.Text=SetupService.DataReady&&!redux?"Native game data is ready":"No ROM selected";panel.Controls.Add(rom);
  choose=Theme.Button("Choose EarthBound ROM",Choose);choose.Width=250;choose.Visible=redux||(!SetupService.DataReady&&!soundtrackOnly);panel.Controls.Add(choose);
  soundtrack.ForeColor=Theme.Ink;soundtrack.Margin=new Padding(0,8,0,8);soundtrack.Visible=!soundtrackOnly;panel.Controls.Add(soundtrack);
  bar.Width=575;bar.Height=22;bar.Visible=false;panel.Controls.Add(bar);status.Width=575;status.AutoSize=false;status.Height=48;panel.Controls.Add(status);
  var actions=new FlowLayoutPanel(){Width=575,Height=60,FlowDirection=FlowDirection.LeftToRight};start=Theme.Button(redux?"Build Redux test edition":soundtrackOnly?"Verify / install soundtrack":"Build my PC edition",Begin,true);cancel=Theme.Button("Cancel",CancelSetup);start.Enabled=!redux&&(SetupService.DataReady||soundtrackOnly);actions.Controls.Add(start);actions.Controls.Add(cancel);panel.Controls.Add(actions);
 }
 void Choose(){using var d=new OpenFileDialog(){Title="Choose your EarthBound (USA) ROM",Filter="SNES ROM (*.sfc;*.smc)|*.sfc;*.smc|All files (*.*)|*.*"};if(d.ShowDialog(this)!=DialogResult.OK)return;rom.Text=d.FileName;start.Enabled=true;}
 async void Begin(){
  if(Completed){Close();return;}
  choose.Enabled=start.Enabled=soundtrack.Enabled=false;bar.Visible=true;bar.Style=ProgressBarStyle.Continuous;stop=new();
  var report=new Progress<SetupProgress>(p=>{status.Text=p.Detail;if(p.Total>0){bar.Style=ProgressBarStyle.Continuous;bar.Value=(int)Math.Clamp(p.Done*100/Math.Max(1,p.Total),0,100);}else bar.Style=ProgressBarStyle.Marquee;});
  try {
   string? path=SetupService.DataReady&&!redux?null:rom.Text;var result=await SetupService.InstallAsync(path,soundtrack.Visible?soundtrack.Checked:true,report,stop.Token);
   if(redux)await ReduxProfileService.BuildAsync(rom.Text,report,stop.Token);
   Completed=true;bar.Style=ProgressBarStyle.Continuous;bar.Value=100;status.Text=redux?"Redux development profile is ready. Full playthrough remains unverified.":result.MsuTracks>0?$"Ready to play. {result.MsuTracks} soundtrack tracks are verified.":"Ready to play. You can install the MSU soundtrack later from Audio.";
   start.Text="Done";start.Enabled=true;cancel.Visible=false;
  } catch(OperationCanceledException){status.Text="Setup canceled. Completed files were kept, so you can continue later.";start.Enabled=true;choose.Enabled=redux||!SetupService.DataReady;soundtrack.Enabled=true;}
  catch(Exception e)when(e is IOException or InvalidDataException or ArgumentException or UnauthorizedAccessException or System.ComponentModel.Win32Exception or HttpRequestException){status.Text=e.Message;status.ForeColor=Theme.Error;start.Enabled=true;choose.Enabled=redux||!SetupService.DataReady;soundtrack.Enabled=true;}
 }
 void CancelSetup(){if(stop!=null&&!stop.IsCancellationRequested){stop.Cancel();return;}DialogResult=DialogResult.Cancel;Close();}
 protected override void Dispose(bool disposing){if(disposing)stop?.Dispose();base.Dispose(disposing);}
}
