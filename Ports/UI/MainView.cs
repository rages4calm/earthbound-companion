// SPDX-License-Identifier: GPL-3.0-or-later
using System.Diagnostics;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Layout;
using Avalonia.Platform.Storage;
using Avalonia.Threading;

namespace EarthBoundCompanion;
public sealed class MainView : UserControl {
 readonly Settings settings=Settings.Load();
 readonly TextBlock status=new(){TextWrapping=Avalonia.Media.TextWrapping.Wrap};
 readonly WrapPanel actions=new(){Orientation=Orientation.Horizontal};
 readonly Func<Settings,bool,SeedRecord?,Task>? mobileLaunch;
 readonly Action? mobileReturn;
 readonly DispatcherTimer settingsMonitor=new(){Interval=TimeSpan.FromMilliseconds(350)};
 bool gameRunning,requestSeen;
 public bool IsBusy=>busy;
 readonly ComboBox seeds=new(){MinWidth=320};
 readonly List<Action> capture=[];
 readonly List<Action> refresh=[];
 readonly List<Control> busyControls=[];
 bool busy;
 public MainView(Func<Settings,bool,SeedRecord?,Task>? mobileLaunch=null,Action? mobileReturn=null) {
  this.mobileLaunch=mobileLaunch;
  this.mobileReturn=mobileReturn;
  var content=new StackPanel{Margin=new Thickness(24),Spacing=14};
  content.Children.Add(new TextBlock{Text="EarthBound Companion",FontSize=28,FontWeight=Avalonia.Media.FontWeight.Bold});
  content.Children.Add(new TextBlock{Text="Platform preview · Uses separate data and saves. Community gameplay testing is pending.",TextWrapping=Avalonia.Media.TextWrapping.Wrap});
  actions.Children.Add(Action("Play",()=>Launch(false)));actions.Children.Add(Action("Resume quick save",()=>Launch(true)));
  var saveSettings=new Button{Content="Save settings / return to game",Margin=new Thickness(0,0,8,4)};
  saveSettings.Click+=(_,_)=>{if(busy&&!gameRunning)return;try{Capture();settings.Save();if(gameRunning){File.WriteAllText(Settings.PathTo("settings.applied"),"");File.Delete(Settings.PathTo("settings.request"));requestSeen=false;mobileReturn?.Invoke();}status.Text="Settings saved.";}catch(Exception e){status.Text=e.Message;}};
  actions.Children.Add(saveSettings);
  content.Children.Add(actions);
  var pages=new[]{Setup(),Display(),Gameplay(),Controls(),Shuffle(),Recovery()};
  var section=new ComboBox{ItemsSource=new[]{"Game & setup","Display","Sound & gameplay","Controls","Story Shuffle","Saves & mods"},SelectedIndex=0};content.Children.Add(section);
  var activePage=new ContentControl{Content=pages[0]};section.SelectionChanged+=(_,_)=>{if(section.SelectedIndex>=0)activePage.Content=pages[section.SelectedIndex];};content.Children.Add(activePage);
  content.Children.Add(status);Content=new ScrollViewer{Content=content};
  status.Text=$"Data folder: {Settings.Root}\nWindows installations are not imported or modified.";
  settingsMonitor.Tick+=(_,_)=>{if(!gameRunning||!File.Exists(Settings.PathTo("settings.request"))){requestSeen=false;return;}if(requestSeen)return;requestSeen=true;settings.ReadEngine();Refresh();status.Text="Game paused for settings. Save settings to resume.";if(TopLevel.GetTopLevel(this) is Window window){window.Show();window.Activate();}};
  settingsMonitor.Start();DetachedFromVisualTree+=(_,_)=>settingsMonitor.Stop();

 }
 static TabItem Tab(string title,Control page)=>new(){Header=title,Content=new ScrollViewer{Content=page,MaxHeight=510}};
 static StackPanel Page()=>new(){Margin=new Thickness(4,14,4,8),Spacing=10};
 static TextBlock Text(string text)=>new(){Text=text,TextWrapping=Avalonia.Media.TextWrapping.Wrap};
 Button Action(string label,Func<Task> task) {
  var b=new Button{Content=new TextBlock{Text=label,TextWrapping=Avalonia.Media.TextWrapping.Wrap},Margin=new Thickness(0,0,8,4)};busyControls.Add(b);
  b.Click+=async(_,_)=>{if(busy)return;SetBusy(true);try{await task();}catch(Exception e){status.Text=e.Message;}finally{SetBusy(false);}};
  return b;
 }
 void SetBusy(bool value){busy=value;foreach(var c in busyControls)c.IsEnabled=!value;}
 void Capture(){foreach(var save in capture)save();settings.Validate();}
 void Refresh(){foreach(var load in refresh)load();}
 CheckBox Check(StackPanel panel,string label,Func<bool> get,Action<bool> set){var c=new CheckBox{Content=label,IsChecked=get()};panel.Children.Add(c);capture.Add(()=>set(c.IsChecked==true));refresh.Add(()=>c.IsChecked=get());return c;}
 ComboBox Choice(StackPanel panel,string label,string[] values,Func<int> get,Action<int> set){panel.Children.Add(Text(label));var c=new ComboBox{ItemsSource=values,SelectedIndex=get(),MinWidth=240};panel.Children.Add(c);capture.Add(()=>set(c.SelectedIndex));refresh.Add(()=>c.SelectedIndex=get());return c;}
 NumericUpDown Number(StackPanel panel,string label,int min,int max,Func<int> get,Action<int> set){panel.Children.Add(Text(label));var c=new NumericUpDown{Minimum=min,Maximum=max,Value=get(),Width=170,HorizontalAlignment=HorizontalAlignment.Left};panel.Children.Add(c);capture.Add(()=>set((int)(c.Value??min)));refresh.Add(()=>c.Value=get());return c;}
 async Task<string?> Pick(string title,params string[] patterns){var files=await TopLevel.GetTopLevel(this)!.StorageProvider.OpenFilePickerAsync(new(){Title=title,AllowMultiple=false,FileTypeFilter=[new FilePickerFileType(title){Patterns=patterns}]});var file=files.FirstOrDefault();if(file==null)return null;var local=file.TryGetLocalPath();if(local!=null)return local;var temp=Path.Combine(Settings.User,"Imports",Guid.NewGuid().ToString("N")+"-"+Path.GetFileName(file.Name));Directory.CreateDirectory(Path.GetDirectoryName(temp)!);await using var input=await file.OpenReadAsync();await using var output=File.Create(temp);byte[] buffer=new byte[65536];long count=0;int n;while((n=await input.ReadAsync(buffer))>0){count+=n;if(count>128L*1024*1024)throw new IOException("Import exceeds the supported size limit.");await output.WriteAsync(buffer.AsMemory(0,n));}return temp;}
 async Task ExportFile(string title,string name,byte[] data){var file=await TopLevel.GetTopLevel(this)!.StorageProvider.SaveFilePickerAsync(new(){Title=title,SuggestedFileName=name});if(file==null)return;await using var stream=await file.OpenWriteAsync();await stream.WriteAsync(data);status.Text="Exported "+file.Name;}
 StackPanel Setup(){var p=Page();
  p.Children.Add(Text("Import your privately generated game data, or use a platform setup helper when supplied. The preview never bundles game assets."));
  p.Children.Add(Action("Import Original assets.pak",async()=>{var path=await Pick("Original asset pack","*.pak");if(path==null)return;var data=await File.ReadAllBytesAsync(path);var policy=ProgressionGuard.CheckBase(data);if(policy.ContentId!="earthbound-usa")throw new InvalidDataException("Choose an Original EarthBound pack.");Directory.CreateDirectory(Settings.BaseGame);var target=Path.Combine(Settings.BaseGame,"assets.pak");if(File.Exists(target)&&StoryShuffle.HashFile(target)!=StoryShuffle.Hash(data))throw new IOException("An Original pack already exists. It was preserved; use a separate preview data folder for another version.");File.WriteAllBytes(target+".import",data);File.Move(target+".import",target,true);status.Text="Original data imported. Choose Original to play.";}));
  p.Children.Add(Action("Import Redux assets.pak",async()=>{var path=await Pick("Redux asset pack","*.pak");if(path==null)return;var data=await File.ReadAllBytesAsync(path);var policy=ProgressionGuard.CheckBase(data);string hash=StoryShuffle.Hash(data);if(policy.ContentId!=ReduxProfileService.ContentId||!ReduxStoryUpgrade.IsCurrent(hash))throw new InvalidDataException("Choose a current, supported Redux pack.");var folder=ReduxProfileService.DirectoryPath;if(Directory.Exists(folder))throw new IOException("A Redux profile already exists and was preserved.");Directory.CreateDirectory(folder);await File.WriteAllBytesAsync(ReduxProfileService.Pack,data);await File.WriteAllTextAsync(Path.Combine(folder,"profile.json"),System.Text.Json.JsonSerializer.Serialize(new {contentId=policy.ContentId,assetPackSha256=hash}));status.Text="Redux data imported with its own save profile.";}));
  if(mobileLaunch==null){
   p.Children.Add(Action("Set up Original from ROM",async()=>{var path=await Pick("Clean EarthBound USA ROM","*.sfc","*.smc");if(path==null)return;await SetupService.InstallAsync(path,false,new Progress<SetupProgress>(v=>status.Text=v.Detail));status.Text="Original setup complete.";}));
   p.Children.Add(Action("Build Redux from ROM",async()=>{var path=await Pick("Clean EarthBound USA ROM","*.sfc","*.smc");if(path==null)return;await ReduxProfileService.BuildAsync(path,new Progress<SetupProgress>(v=>status.Text=v.Detail));status.Text="Redux setup complete.";}));
  }else p.Children.Add(Text("Prepare the asset packs with Companion on a computer, then transfer them privately to your phone. ROM conversion on the phone is not available yet."));
  p.Children.Add(Action("Select Original",()=>{settings.AssetPack="";settings.ReduxDevelopmentEnabled=false;settings.Save();seeds.SelectedItem=null;status.Text="Original selected.";return Task.CompletedTask;}));
  p.Children.Add(Action("Select Redux",()=>{ReduxProfileService.Select(settings);seeds.SelectedItem=null;status.Text="Redux selected.";return Task.CompletedTask;}));
  return p;
 }
 StackPanel Display(){var p=Page();
  Choice(p,"Preset",["Enhanced","Classic","CRT","Easygoing","Custom"],()=>settings.PresetIndex(),_=>{}).SelectionChanged+=(_,e)=>{if(e.AddedItems.Count>0&&e.AddedItems[0] is string name&&name!="Custom"){settings.Preset(name);Refresh();}};
  Number(p,"Window width",640,7680,()=>settings.Width,v=>settings.Width=v);Number(p,"Window height",480,4320,()=>settings.Height,v=>settings.Height=v);
  Check(p,"Fullscreen",()=>settings.Fullscreen,v=>settings.Fullscreen=v);Check(p,"Integer scaling",()=>settings.IntegerScale,v=>settings.IntegerScale=v);
  Choice(p,"Filter",["Nearest","Scale2x","Linear"],()=>settings.Filter,v=>settings.Filter=v);Choice(p,"Aspect ratio",["Widescreen","4:3","Ultrawide"],()=>settings.Aspect,v=>settings.Aspect=v);
  Check(p,"Wide field of view",()=>settings.WideFov,v=>settings.WideFov=v);Check(p,"Depth effect",()=>settings.TiltShift,v=>settings.TiltShift=v);Check(p,"Color grading",()=>settings.ColorGrading,v=>settings.ColorGrading=v);Check(p,"Scanlines",()=>settings.Scanlines,v=>settings.Scanlines=v);
  Check(p,"Original title presentation in Redux",()=>settings.OriginalTitleScreen,v=>settings.OriginalTitleScreen=v);
  p.Children.Add(Text("External Slang presets are Windows-only in this first preview. The built-in display effects above remain available."));return p;
 }
 StackPanel Gameplay(){var p=Page();
  Number(p,"Sound volume",0,100,()=>settings.Volume,v=>settings.Volume=v);Number(p,"Music volume",0,100,()=>settings.MusicVolume,v=>settings.MusicVolume=v);Check(p,"HQ audio",()=>settings.HqAudio,v=>settings.HqAudio=v);
  p.Children.Add(Action("Install / verify MSU soundtrack",async()=>{await SetupService.InstallAsync(null,true,new Progress<SetupProgress>(v=>status.Text=v.Detail));status.Text="Music installation verified.";}));
  Choice(p,"Hold Y to sprint",["Off","1.5×","2×"],()=>settings.Sprint,v=>settings.Sprint=v);Check(p,"Instant text",()=>settings.InstantText,v=>settings.InstantText=v);Check(p,"Disable homesickness",()=>settings.NoHomesickness,v=>settings.NoHomesickness=v);Check(p,"Disable Dad calls",()=>settings.NoDadCalls,v=>settings.NoDadCalls=v);
  Number(p,"Experience multiplier",1,16,()=>settings.Exp,v=>settings.Exp=v);Number(p,"Money multiplier",1,16,()=>settings.Money,v=>settings.Money=v);Number(p,"Fast-forward multiplier",2,16,()=>settings.FastForward,v=>settings.FastForward=v);Number(p,"Quick-save slot (0–4)",0,4,()=>settings.QuickSlot,v=>settings.QuickSlot=v);return p;
 }
 StackPanel Controls(){var p=Page();p.Children.Add(Text("SDL keyboard scancodes and controller button IDs match the Windows game's configuration. Keyboard: Enter confirm, Z cancel, arrows move, Left Shift sprint, Tab fast-forward, F6/F7 save/load. Controllers are read by the game."));
  Check(p,"Nintendo face-button labels",()=>settings.NintendoFaceLabels,v=>settings.NintendoFaceLabels=v);Number(p,"Stick deadzone",2000,30000,()=>settings.Deadzone,v=>settings.Deadzone=v);
  string[] names=["A","B","X","Y","L","R","Start","Select","Up","Down","Left","Right","Fast-forward","Save","Load","FPS","Zoom","Fullscreen","Screenshot","Pause","Settings"];
  for(int i=0;i<names.Length;i++){int n=i;Number(p,names[i]+" keyboard scancode",0,511,()=>settings.Keys[n],v=>settings.Keys[n]=v);Number(p,names[i]+" controller button (-1 disables)",-1,16,()=>settings.Buttons[n],v=>settings.Buttons[n]=v);}return p;
 }
 StackPanel Shuffle(){var p=Page();p.Children.Add(Text("Same Story Shuffle v4 recipes, progression rules and separate seed saves as Windows. Select a game mode before generating a seed."));var seed=new TextBox{Watermark="Seed name"};p.Children.Add(seed);var mode=new ComboBox{ItemsSource=new[]{"Balanced","Surprise"},SelectedIndex=1};p.Children.Add(mode);var options=new List<CheckBox>();foreach(var name in new[]{"Gifts","Shops","Enemy stats","Enemy drops","Wild encounters"}){var c=new CheckBox{Content=name,IsChecked=true};options.Add(c);p.Children.Add(c);}
  p.Children.Add(Action("Generate seed",async()=>{Capture();settings.Save();var o=new ShuffleOptions{Mode=mode.SelectedIndex==0?"Balanced":"Surprise",Gifts=options[0].IsChecked==true,Shops=options[1].IsChecked==true,EnemyStats=options[2].IsChecked==true,EnemyDrops=options[3].IsChecked==true,EnemyEncounters=options[4].IsChecked==true};var built=await Task.Run(()=>StoryShuffle.Generate(seed.Text??"",o));seeds.ItemsSource=StoryShuffle.List();seeds.SelectedItem=built;status.Text="Seed generated and selected. Press Play.";}));
  p.Children.Add(Action("Import recipe",async()=>{var path=await Pick("Seed recipe","*.json");if(path==null)return;Capture();settings.Save();var r=StoryShuffle.ImportRecipe(path);var built=await Task.Run(()=>StoryShuffle.Generate(r.Seed,r.Options,r.BaseHash,r.Version));seeds.ItemsSource=StoryShuffle.List();seeds.SelectedItem=built;status.Text="Recipe rebuilt with its original identity.";}));
  seeds.ItemsSource=StoryShuffle.List();p.Children.Add(seeds);p.Children.Add(Action("Play regular story instead",()=>{seeds.SelectedItem=null;status.Text="Regular story selected.";return Task.CompletedTask;}));return p;
 }
 StackPanel Recovery(){var p=Page();p.Children.Add(Text("Backups are kept in this preview's data folder. Across platforms, transfer normal in-game phone saves; quick saves remain restricted to their exact engine build."));
  p.Children.Add(Action("Back up selected adventure",()=>{Settings.SessionDirectory=(seeds.SelectedItem as SeedRecord)?.Session;Capture();settings.Save();status.Text="Backup: "+Settings.Backup(true);Settings.SessionDirectory=null;return Task.CompletedTask;}));
  p.Children.Add(Action("Restore phone save from backup",async()=>{var path=await Pick("Companion save backup","*.zip");if(path==null)return;Settings.SessionDirectory=(seeds.SelectedItem as SeedRecord)?.Session;try{var result=SaveRecovery.Restore(path,Settings.Game,true);status.Text=$"Restored {result.Files} files. Previous data: {result.PreviousBackup}";}finally{Settings.SessionDirectory=null;}}));
  p.Children.Add(Action("Import QoL profile",async()=>{var path=await Pick("Companion mod profile","*.json");if(path==null)return;settings.ImportProfile(path);Refresh();settings.Save();status.Text="Profile imported.";}));
  p.Children.Add(Action("Export settings",async()=>{Capture();await ExportFile("Export settings","companion-settings.json",System.Text.Json.JsonSerializer.SerializeToUtf8Bytes(settings,Settings.JsonOptions));}));
  p.Children.Add(Action("Export phone save",async()=>{Settings.SessionDirectory=(seeds.SelectedItem as SeedRecord)?.Session;try{Capture();settings.Save();await ExportFile("Export phone save","earthbound.srm",await File.ReadAllBytesAsync(Settings.PathTo("saves/earthbound.srm")));}finally{Settings.SessionDirectory=null;}}));
  p.Children.Add(Action("Import phone save",async()=>{var path=await Pick("Phone save for this adventure","*.srm");if(path==null)return;var data=await File.ReadAllBytesAsync(path);if(data.Length!=8192)throw new InvalidDataException("A phone save must be exactly 8192 bytes. Select its matching game edition and seed before importing.");Settings.SessionDirectory=(seeds.SelectedItem as SeedRecord)?.Session;try{Capture();settings.Save();string previous=Settings.Backup(true);var target=Settings.PathTo("saves/earthbound.srm");Directory.CreateDirectory(Path.GetDirectoryName(target)!);await File.WriteAllBytesAsync(target+".import",data);File.Move(target+".import",target,true);status.Text="Phone save imported. Previous data: "+previous;}finally{Settings.SessionDirectory=null;}}));
  p.Children.Add(Text("Data: "+Settings.Root));return p;
 }
 async Task Launch(bool resume){
  Capture();gameRunning=true;requestSeen=false;
  try {
   if(mobileLaunch!=null){await mobileLaunch(settings,resume,seeds.SelectedItem as SeedRecord);status.Text="Returned from game.";}
   else {if(!OperatingSystem.IsWindows())settings.ShaderPreset="";using var process=GameLaunch.Start(settings,resume,seeds.SelectedItem as SeedRecord);status.Text="Game running. The Settings shortcut pauses the game and opens this window.";await process.WaitForExitAsync();status.Text=process.ExitCode==0?"Game closed. Saves remain in your preview data folder.":$"Game exited with code {process.ExitCode}. See the selected adventure's game.log.";}
  }finally{gameRunning=false;requestSeen=false;Settings.SessionDirectory=null;settings.ReadEngine();Refresh();}
 }
}
