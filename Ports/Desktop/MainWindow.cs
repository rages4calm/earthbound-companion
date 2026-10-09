// SPDX-License-Identifier: GPL-3.0-or-later
using System.Diagnostics;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Layout;
using Avalonia.Platform.Storage;
using Avalonia.Threading;

namespace EarthBoundCompanion;
public sealed class MainWindow : Window {
 readonly Settings settings=Settings.Load();
 readonly TextBlock status=new(){TextWrapping=Avalonia.Media.TextWrapping.Wrap};
 readonly StackPanel actions=new(){Orientation=Orientation.Horizontal,Spacing=8};
 readonly ComboBox seeds=new(){MinWidth=320};
 readonly List<Action> capture=[];
 readonly List<Action> refresh=[];
 readonly List<Control> busyControls=[];
 bool busy;
 public MainWindow() {
  Title="EarthBound Companion · Platform Preview";Width=1020;Height=780;MinWidth=720;MinHeight=540;
  var content=new StackPanel{Margin=new Thickness(24),Spacing=14};
  content.Children.Add(new TextBlock{Text="EarthBound Companion",FontSize=28,FontWeight=Avalonia.Media.FontWeight.Bold});
  content.Children.Add(new TextBlock{Text="Linux / macOS preview · Uses separate data and saves. Community gameplay testing is pending.",TextWrapping=Avalonia.Media.TextWrapping.Wrap});
  actions.Children.Add(Action("Play",()=>Launch(false)));actions.Children.Add(Action("Resume quick save",()=>Launch(true)));
  actions.Children.Add(Action("Save settings",()=>{Capture();settings.Save();return Task.CompletedTask;}));
  content.Children.Add(actions);
  var tabs=new TabControl();content.Children.Add(tabs);
  tabs.ItemsSource=new[]{Tab("Game & setup",Setup()),Tab("Display",Display()),Tab("Sound & gameplay",Gameplay()),Tab("Controls",Controls()),Tab("Story Shuffle",Shuffle()),Tab("Saves & mods",Recovery())};
  content.Children.Add(status);Content=content;
  status.Text=$"Data folder: {Settings.Root}\nWindows installations are not imported or modified.";
  Closing+=(_,e)=>{if(busy){e.Cancel=true;status.Text="Wait for the active operation or close the game before closing Companion.";}};
 }
 static TabItem Tab(string title,Control page)=>new(){Header=title,Content=new ScrollViewer{Content=page,MaxHeight=510}};
 static StackPanel Page()=>new(){Margin=new Thickness(4,14,4,8),Spacing=10};
 static TextBlock Text(string text)=>new(){Text=text,TextWrapping=Avalonia.Media.TextWrapping.Wrap};
 Button Action(string label,Func<Task> task) {
  var b=new Button{Content=label};busyControls.Add(b);
  b.Click+=async(_,_)=>{if(busy)return;SetBusy(true);try{await task();}catch(Exception e){status.Text=e.Message;}finally{SetBusy(false);}};
  return b;
 }
 void SetBusy(bool value){busy=value;foreach(var c in busyControls)c.IsEnabled=!value;}
 void Capture(){foreach(var save in capture)save();settings.Validate();}
 void Refresh(){foreach(var load in refresh)load();}
 CheckBox Check(StackPanel panel,string label,Func<bool> get,Action<bool> set){var c=new CheckBox{Content=label,IsChecked=get()};panel.Children.Add(c);capture.Add(()=>set(c.IsChecked==true));refresh.Add(()=>c.IsChecked=get());return c;}
 ComboBox Choice(StackPanel panel,string label,string[] values,Func<int> get,Action<int> set){panel.Children.Add(Text(label));var c=new ComboBox{ItemsSource=values,SelectedIndex=get(),MinWidth=240};panel.Children.Add(c);capture.Add(()=>set(c.SelectedIndex));refresh.Add(()=>c.SelectedIndex=get());return c;}
 NumericUpDown Number(StackPanel panel,string label,int min,int max,Func<int> get,Action<int> set){panel.Children.Add(Text(label));var c=new NumericUpDown{Minimum=min,Maximum=max,Value=get(),Width=170,HorizontalAlignment=HorizontalAlignment.Left};panel.Children.Add(c);capture.Add(()=>set((int)(c.Value??min)));refresh.Add(()=>c.Value=get());return c;}
 async Task<string?> Pick(string title,params string[] patterns){var files=await StorageProvider.OpenFilePickerAsync(new(){Title=title,AllowMultiple=false,FileTypeFilter=[new FilePickerFileType(title){Patterns=patterns}]});return files.FirstOrDefault()?.TryGetLocalPath();}
 async Task<string?> SaveFile(string title,string name){var file=await StorageProvider.SaveFilePickerAsync(new(){Title=title,SuggestedFileName=name});return file?.TryGetLocalPath();}
 StackPanel Setup(){var p=Page();
  p.Children.Add(Text("Import your privately generated game data, or use a platform setup helper when supplied. The preview never bundles game assets."));
  p.Children.Add(Action("Import Original assets.pak",async()=>{var path=await Pick("Original asset pack","*.pak");if(path==null)return;var data=await File.ReadAllBytesAsync(path);var policy=ProgressionGuard.CheckBase(data);if(policy.ContentId!="earthbound-usa")throw new InvalidDataException("Choose an Original EarthBound pack.");Directory.CreateDirectory(Settings.BaseGame);var target=Path.Combine(Settings.BaseGame,"assets.pak");if(File.Exists(target)&&StoryShuffle.HashFile(target)!=StoryShuffle.Hash(data))throw new IOException("An Original pack already exists. It was preserved; use a separate preview data folder for another version.");File.WriteAllBytes(target+".import",data);File.Move(target+".import",target,true);status.Text="Original data imported. Choose Original to play.";}));
  p.Children.Add(Action("Import Redux assets.pak",async()=>{var path=await Pick("Redux asset pack","*.pak");if(path==null)return;var data=await File.ReadAllBytesAsync(path);var policy=ProgressionGuard.CheckBase(data);string hash=StoryShuffle.Hash(data);if(policy.ContentId!=ReduxProfileService.ContentId||!ReduxStoryUpgrade.IsCurrent(hash))throw new InvalidDataException("Choose a current, supported Redux pack.");var folder=ReduxProfileService.DirectoryPath;if(Directory.Exists(folder))throw new IOException("A Redux profile already exists and was preserved.");Directory.CreateDirectory(folder);await File.WriteAllBytesAsync(ReduxProfileService.Pack,data);await File.WriteAllTextAsync(Path.Combine(folder,"profile.json"),System.Text.Json.JsonSerializer.Serialize(new {contentId=policy.ContentId,assetPackSha256=hash}));status.Text="Redux data imported with its own save profile.";}));
  p.Children.Add(Action("Set up Original from ROM",async()=>{var path=await Pick("Clean EarthBound USA ROM","*.sfc","*.smc");if(path==null)return;await SetupService.InstallAsync(path,false,new Progress<SetupProgress>(v=>status.Text=v.Detail));status.Text="Original setup complete.";}));
  p.Children.Add(Action("Build Redux from ROM",async()=>{var path=await Pick("Clean EarthBound USA ROM","*.sfc","*.smc");if(path==null)return;await ReduxProfileService.BuildAsync(path,new Progress<SetupProgress>(v=>status.Text=v.Detail));status.Text="Redux setup complete.";}));
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
  p.Children.Add(Action("Export settings",async()=>{Capture();var path=await SaveFile("Export settings","companion-settings.json");if(path!=null)await File.WriteAllTextAsync(path,System.Text.Json.JsonSerializer.Serialize(settings,Settings.JsonOptions));}));
  p.Children.Add(Text("Data: "+Settings.Root));return p;
 }
 async Task Launch(bool resume){Capture();if(!OperatingSystem.IsWindows())settings.ShaderPreset="";using var process=GameLaunch.Start(settings,resume,seeds.SelectedItem as SeedRecord);status.Text="Game running. Settings are available after you close the game.";await process.WaitForExitAsync();Settings.SessionDirectory=null;settings.ReadEngine();Refresh();status.Text=process.ExitCode==0?"Game closed. Saves remain in your preview data folder.":$"Game exited with code {process.ExitCode}. See the selected adventure's game.log.";}
}
