using System.Diagnostics;
using System.Drawing.Drawing2D;
using System.Text.Json;
namespace EarthBoundCompanion;

static class Program {
 [STAThread]static void Main(string[] args){
  ApplicationConfiguration.Initialize();
  int nativeRecovery=Array.IndexOf(args,"--native-recovery-test");if(nativeRecovery>=0&&nativeRecovery+1<args.Length){NativeRecoveryTests.Run(args[nativeRecovery+1]);return;}
  int checkSeed=Array.IndexOf(args,"--check-seed");if(checkSeed>=0){try{if(checkSeed+1>=args.Length)throw new ArgumentException("Supply a saved seed folder.");var seed=StoryShuffle.Read(args[checkSeed+1]);StoryShuffle.Verify(seed);Console.WriteLine(JsonSerializer.Serialize(new {seed.Seed,seed.Version,Safety=ProgressionGuard.Report()},Settings.JsonOptions));}catch(Exception e)when(e is IOException or InvalidDataException or ArgumentException or UnauthorizedAccessException or JsonException){Console.Error.WriteLine(e.Message);Environment.ExitCode=1;}return;}
 int shuffleTest=Array.IndexOf(args,"--randomizer-test");if(shuffleTest>=0&&shuffleTest+1<args.Length){RandomizerTests.Run(args[shuffleTest+1]);return;}
  int setupRom=Array.IndexOf(args,"--setup-rom");if(setupRom>=0){try{if(setupRom+1>=args.Length)throw new ArgumentException("Supply an EarthBound (USA) ROM path.");SetupService.InstallAsync(args[setupRom+1],args.Contains("--with-msu"),new Progress<SetupProgress>(p=>Console.WriteLine(p.Detail))).GetAwaiter().GetResult();Console.WriteLine("Setup complete.");}catch(Exception e){Console.Error.WriteLine(e.Message);Environment.ExitCode=1;}return;}
  int seedArgument=Array.IndexOf(args,"--generate-seed"),recipeArgument=Array.IndexOf(args,"--recipe");
  if(seedArgument>=0||recipeArgument>=0){
   try {
    SeedRecord seed;
    if(recipeArgument>=0){if(recipeArgument+1>=args.Length)throw new ArgumentException("Supply a Companion seed recipe path.");var recipe=StoryShuffle.ImportRecipe(args[recipeArgument+1]);seed=StoryShuffle.Generate(recipe.Seed,recipe.Options,recipe.BaseHash);}
    else{if(seedArgument+1>=args.Length)throw new ArgumentException("Supply a seed number or phrase.");seed=StoryShuffle.Generate(args[seedArgument+1],new ShuffleOptions {Mode=args.Contains("--surprise")?"Surprise":"Balanced"});}
    Console.WriteLine(Path.Combine(seed.Folder,"seed.json"));
   }catch(Exception e)when(e is IOException or InvalidDataException or ArgumentException or UnauthorizedAccessException or JsonException){Console.Error.WriteLine(e.Message);Environment.ExitCode=1;}
   return;
  }
  Input.Init();
  if(args.Contains("--configure")){Settings.Load().Save();Input.Quit();return;}
  if(args.Contains("--selftest")){SelfTest.Run();Input.Quit();return;}
  Application.Run(new MainForm(args));Input.Quit();
 }
}
static class Theme {
 public static Color Canvas=Color.FromArgb(26,24,42),Rail=Color.FromArgb(18,16,31),Surface=Color.FromArgb(42,38,62),Ink=Color.FromArgb(247,243,255),Muted=Color.FromArgb(194,182,216),Line=Color.FromArgb(80,72,104),Gold=Color.FromArgb(250,216,112),Green=Color.FromArgb(158,219,179),Error=Color.FromArgb(255,166,162);
 public static Font Font(float size=11,FontStyle style=FontStyle.Regular)=>new("Segoe UI",size,style);
 public static Label Text(string text,float size=11,Color? color=null)=>new(){Text=text,AutoSize=true,Font=Font(size),ForeColor=color??Ink,Margin=new Padding(0,0,0,8),MaximumSize=new Size(730,0)};
 public static Button Button(string text,Action click,bool primary=false){var b=new ActionButton(){Text=text,UseMnemonic=false,AutoSize=false,Size=new Size(190,44),FlatStyle=FlatStyle.Flat,BackColor=primary?Gold:Surface,ForeColor=primary?Rail:Ink,Font=Font(11,FontStyle.Bold),Cursor=Cursors.Hand,Margin=new Padding(0,4,12,8)};b.FlatAppearance.BorderColor=primary?Gold:Line;b.FlatAppearance.MouseOverBackColor=primary?Color.FromArgb(255,230,150):Color.FromArgb(63,55,89);b.Click+=(_,_)=>click();return b;}
}
sealed class ActionButton : Button {
 protected override void OnPaint(PaintEventArgs e){base.OnPaint(e);bool hover=Enabled&&ClientRectangle.Contains(PointToClient(Cursor.Position));e.Graphics.Clear(hover?FlatAppearance.MouseOverBackColor:BackColor);using var pen=new Pen(FlatAppearance.BorderColor);e.Graphics.DrawRectangle(pen,0,0,Width-1,Height-1);TextRenderer.DrawText(e.Graphics,Text,Font,ClientRectangle,Enabled?ForeColor:Theme.Muted,TextFormatFlags.HorizontalCenter|TextFormatFlags.VerticalCenter|TextFormatFlags.EndEllipsis|TextFormatFlags.NoPrefix);if(Focused)ControlPaint.DrawFocusRectangle(e.Graphics,new Rectangle(4,4,Width-8,Height-8),ForeColor,BackColor);}
}
sealed class Scene : Control {
 Image? image;
 public Scene(){DoubleBuffered=true;Height=232;Margin=new Padding(0,8,0,24);TabStop=false;string p=Path.Combine(Settings.Root,"Media","onett.png");if(File.Exists(p))image=Image.FromFile(p);}
 protected override void OnPaint(PaintEventArgs e){base.OnPaint(e);e.Graphics.Clear(Theme.Rail);if(image==null){PaintFallback(e.Graphics);return;}e.Graphics.InterpolationMode=InterpolationMode.NearestNeighbor;
  float r=Math.Max((float)Width/image.Width,(float)Height/image.Height);int w=(int)(image.Width*r),h=(int)(image.Height*r);e.Graphics.DrawImage(image,new Rectangle((Width-w)/2,(Height-h)/2,w,h));}
 void PaintFallback(Graphics g){
  g.SmoothingMode=SmoothingMode.AntiAlias;using var sky=new LinearGradientBrush(ClientRectangle,Color.FromArgb(35,25,78),Color.FromArgb(232,115,116),LinearGradientMode.Vertical);g.FillRectangle(sky,ClientRectangle);
  using var moon=new SolidBrush(Color.FromArgb(255,236,166));g.FillEllipse(moon,Width-150,24,74,74);
  using var stars=new SolidBrush(Color.FromArgb(225,243,225));foreach(var p in new[]{new Point(65,37),new Point(160,68),new Point(274,32),new Point(390,75),new Point(535,42),new Point(660,65)})g.FillEllipse(stars,p.X,p.Y,3,3);
  using var far=new SolidBrush(Color.FromArgb(74,65,103));g.FillEllipse(far,-90,112,420,210);g.FillEllipse(far,220,105,510,240);g.FillEllipse(far,590,120,420,220);
  using var ground=new SolidBrush(Color.FromArgb(42,72,68));g.FillRectangle(ground,0,158,Width,Height-158);
  using var road=new SolidBrush(Color.FromArgb(199,162,117));g.FillPolygon(road,new Point[]{new(Width/2-55,158),new(Width/2+55,158),new(Width/2+235,Height),new(Width/2-235,Height)});
  using var house=new SolidBrush(Color.FromArgb(244,215,164));using var roof=new SolidBrush(Color.FromArgb(132,55,72));using var light=new SolidBrush(Theme.Gold);
  foreach(int x in new[]{85,235,Width-305,Width-155}){g.FillRectangle(house,x,139,85,53);g.FillPolygon(roof,new Point[]{new(x-8,141),new(x+42,108),new(x+93,141)});g.FillRectangle(light,x+18,154,15,16);g.FillRectangle(light,x+53,154,15,16);}
 }
 protected override void Dispose(bool disposing){if(disposing)image?.Dispose();base.Dispose(disposing);}
}
sealed partial class MainForm : Form {
 Settings settings=Settings.Load();readonly FlowLayoutPanel nav=new(),page=new();readonly Label status=new();
 readonly System.Windows.Forms.Timer timer=new(){Interval=350};readonly Dictionary<string,Button> navigation=[];
 Process? game;string current="Solo Play";bool settingsRequested;bool captureMode;int captureIndex;string captureDir="";bool capturePrepared;bool captureScrolled;
 readonly string[] pages=["Solo Play","Randomizer","Display","Audio","Gameplay","Controls","Mods & saves"];
 public MainForm(string[] args){
  Text="EarthBound Companion";Font=Theme.Font();BackColor=Theme.Canvas;ForeColor=Theme.Ink;ClientSize=new Size(1120,800);MinimumSize=new Size(990,760);StartPosition=FormStartPosition.CenterScreen;
  if(args.Contains("--compact"))ClientSize=new Size(990,760);
  var layout=new TableLayoutPanel(){Dock=DockStyle.Fill,ColumnCount=2,RowCount=2};layout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,210));layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));layout.RowStyles.Add(new RowStyle(SizeType.Percent,100));layout.RowStyles.Add(new RowStyle(SizeType.Absolute,76));Controls.Add(layout);
  nav.Dock=DockStyle.Fill;nav.FlowDirection=FlowDirection.TopDown;nav.WrapContents=false;nav.BackColor=Theme.Rail;nav.Padding=new Padding(24,32,18,20);layout.Controls.Add(nav,0,0);layout.SetRowSpan(nav,2);
  var brand=Theme.Text("EarthBound",17,Theme.Gold);brand.Font=Theme.Font(17,FontStyle.Bold);brand.AutoSize=false;brand.Size=new Size(166,34);nav.Controls.Add(brand);nav.Controls.Add(Theme.Text("Companion",12,Theme.Muted));nav.Controls.Add(new Panel(){Height=28,Width=160});
  foreach(var name in pages){var b=Theme.Button(name,()=>ShowPage(name));b.Size=new Size(166,46);b.Margin=new Padding(0,0,0,6);navigation[name]=b;nav.Controls.Add(b);}
  nav.Controls.Add(new Panel(){Height=30,Width=160});nav.Controls.Add(Theme.Text("Windows PC edition",10,Theme.Muted));nav.Controls.Add(Theme.Text("Local. Yours to tune.",10,Theme.Muted));
  page.Dock=DockStyle.Fill;page.FlowDirection=FlowDirection.TopDown;page.WrapContents=false;page.AutoScroll=true;page.Padding=new Padding(32,26,24,12);page.SizeChanged+=(_,_)=>ResizePage();layout.Controls.Add(page,1,0);
  var footer=new TableLayoutPanel(){Dock=DockStyle.Fill,ColumnCount=2,Padding=new Padding(32,9,24,10),BackColor=Theme.Rail};footer.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,100));footer.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute,190));layout.Controls.Add(footer,1,1);
  status.Dock=DockStyle.Fill;status.TextAlign=ContentAlignment.MiddleLeft;status.Font=Theme.Font(10);status.ForeColor=Theme.Muted;footer.Controls.Add(status,0,0);footer.Controls.Add(Theme.Button("Apply settings",Apply,true),1,0);
  if(!File.Exists(Path.Combine(Settings.User,"settings.json")))settings.Save();
  ShowPage("Solo Play");Notify("Ready. Your saved settings are loaded.");
  timer.Tick+=Tick;timer.Start();FormClosing+=(_,e)=>{if(generating){e.Cancel=true;Notify("Finishing seed generation. You can close the launcher when it is ready.");return;}if(settingsRequested)Resume();};
  int capture=Array.IndexOf(args,"--capture");if(capture>=0&&capture+1<args.Length){captureMode=true;captureDir=Path.GetFullPath(args[capture+1]);Directory.CreateDirectory(captureDir);}
  Shown+=(_,_)=>{if(!captureMode&&!SetupService.DataReady)OpenSetup(false);};
 }
 void ResizePage(){int w=Math.Max(680,page.ClientSize.Width-page.Padding.Horizontal-22);foreach(Control c in page.Controls)if(c is not Label)c.Width=w;}
 void Notify(string message,bool error=false){status.Text=message;status.ForeColor=error?Theme.Error:Theme.Muted;}
 void Header(string title,string text){var h=Theme.Text(title,25);h.Font=Theme.Font(25,FontStyle.Bold);h.Margin=new Padding(0,0,0,6);page.Controls.Add(h);page.Controls.Add(Theme.Text(text,11,Theme.Muted));page.Controls.Add(new Panel(){Height=12});}
 void Section(string text){var l=Theme.Text(text,13);l.Font=Theme.Font(13,FontStyle.Bold);l.Margin=new Padding(0,16,0,12);page.Controls.Add(l);}
 FlowLayoutPanel Actions(params Button[] buttons){var f=new FlowLayoutPanel(){Height=58,WrapContents=false,Margin=new Padding(0,6,0,12)};f.Controls.AddRange(buttons);page.Controls.Add(f);return f;}
 void Row(string title,string help,Control input){
  var row=new TableLayoutPanel(){Height=78,ColumnCount=2,RowCount=2,Margin=new Padding(0,0,0,8),Padding=new Padding(0,2,0,0)};row.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,64));row.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,36));row.RowStyles.Add(new RowStyle(SizeType.Absolute,28));row.RowStyles.Add(new RowStyle(SizeType.Percent,100));
  var t=Theme.Text(title);t.Margin=new Padding(0);row.Controls.Add(t,0,0);var desc=Theme.Text(help,10,Theme.Muted);desc.MaximumSize=new Size(460,0);row.SizeChanged+=(_,_)=>desc.MaximumSize=new Size(Math.Max(200,(int)(row.ClientSize.Width*.64)-12),0);row.Controls.Add(desc,0,1);input.Dock=DockStyle.Top;input.Margin=new Padding(12,0,4,0);row.Controls.Add(input,1,0);row.SetRowSpan(input,2);page.Controls.Add(row);
 }
 void Check(string title,string help,bool value,Action<bool> set){var c=new CheckBox(){Text="Enabled",Checked=value,AutoSize=true,ForeColor=Theme.Ink,Height=34,AccessibleName=title};c.CheckedChanged+=(_,_)=>set(c.Checked);Row(title,help,c);}
 void Choice(string title,string help,string[] labels,int value,Action<int> set){var c=new ComboBox(){DropDownStyle=ComboBoxStyle.DropDownList,DrawMode=DrawMode.OwnerDrawFixed,ItemHeight=24,BackColor=Theme.Surface,ForeColor=Theme.Ink,Font=Theme.Font(),AccessibleName=title};c.Items.AddRange(labels);c.DrawItem+=(_,e)=>{using var brush=new SolidBrush(Theme.Surface);e.Graphics.FillRectangle(brush,e.Bounds);if(e.Index>=0)TextRenderer.DrawText(e.Graphics,c.Items[e.Index]!.ToString(),c.Font,e.Bounds,(e.State&DrawItemState.Selected)!=0?Theme.Gold:Theme.Ink,TextFormatFlags.Left|TextFormatFlags.VerticalCenter|TextFormatFlags.EndEllipsis);e.DrawFocusRectangle();};c.SelectedIndex=Math.Clamp(value,0,labels.Length-1);c.SelectedIndexChanged+=(_,_)=>set(c.SelectedIndex);Row(title,help,c);}
 void Slider(string title,string help,int value,int max,Action<int> set){var panel=new Panel(){Height=60};var label=Theme.Text(value.ToString(),10,Theme.Gold);label.Dock=DockStyle.Right;label.Width=45;label.AutoSize=false;var bar=new TrackBar(){Minimum=0,Maximum=max,Value=Math.Clamp(value,0,max),TickStyle=TickStyle.None,Dock=DockStyle.Fill,SmallChange=1,LargeChange=5,AccessibleName=title};bar.ValueChanged+=(_,_)=>{set(bar.Value);label.Text=bar.Value.ToString();};panel.Controls.Add(bar);panel.Controls.Add(label);Row(title,help,panel);}
 void ShowPage(string name){
  current=name;page.SuspendLayout();foreach(Control c in page.Controls.Cast<Control>().ToArray())c.Dispose();page.Controls.Clear();page.AutoScrollPosition=Point.Empty;
  foreach(var (n,b) in navigation){b.BackColor=n==name?Theme.Surface:Theme.Rail;b.ForeColor=n==name?Theme.Gold:Theme.Muted;b.FlatAppearance.BorderColor=n==name?Theme.Line:Theme.Rail;}
  switch(name){case "Solo Play":PlayPage();break;case "Randomizer":RandomizerPage();break;case "Display":DisplayPage();break;case "Audio":AudioPage();break;case "Gameplay":GameplayPage();break;case "Controls":ControlsPage();break;default:ModsPage();break;}
  page.Controls.Add(new Panel {Height=32,Margin=Padding.Empty});
  ResizePage();page.ResumeLayout();
 }
 bool Running=>game!=null&&!game.HasExited;
 void PlayPage(){
  Header("A new trip to Onett.","Your native PC edition, with widescreen scenery and enhancements you control.");var scene=new Scene(){Height=200};page.Controls.Add(scene);
  bool ready=File.Exists(Path.Combine(Settings.BaseGame,"earthbound.exe"))&&File.Exists(settings.Pak);
  var state=Theme.Text(ready?"Game data ready":"Game data missing",12,ready?Theme.Green:Theme.Error);page.Controls.Add(state);
  string msu=Directory.Exists(Path.Combine(Settings.Root,"msu"))?$"{Directory.GetFiles(Path.Combine(Settings.Root,"msu"),"*.pcm").Length} music tracks installed":"No MSU pack installed";
  page.Controls.Add(Theme.Text($"{(settings.Aspect==1?"4:3":settings.Aspect==2?"21:9":"16:9")}  ·  {settings.Width} × {settings.Height}  ·  {msu}",11,Theme.Muted));
  var play=Theme.Button(Running?"Game is running":"Play EarthBound",()=>Launch(false),true);play.Enabled=ready&&!Running&&!generating;
  var resume=Theme.Button("Resume quick save",()=>Launch(true));resume.Enabled=ready&&!Running&&!generating&&HasQuickSave();Actions(play,resume);
  if(!ready){Actions(Theme.Button("Set up from your ROM",()=>OpenSetup(false),true));page.Controls.Add(Theme.Text("Choose a clean EarthBound (USA) ROM. Companion verifies it and builds the native PC game data locally; your ROM is never copied or uploaded.",10,Theme.Muted));}
  Actions(Theme.Button("Randomized adventure",()=>ShowPage("Randomizer")));page.Controls.Add(Theme.Text("Generate a Story Shuffle, replay a seed and keep a separate adventure save.",10,Theme.Muted));
  Section("Make it your edition");Choice("Presentation preset","Select a starting point, then tune individual settings.",["Enhanced","Classic","CRT","Easygoing","Custom"],settings.PresetIndex(),i=>{if(i<4){settings.Preset(new[]{"Enhanced","Classic","CRT","Easygoing"}[i]);ShowPage("Solo Play");Notify("Preset selected. Apply settings to save it.");}});
  page.Controls.Add(Theme.Text("F1 settings  ·  F6 save  ·  F7 load  ·  F9 pause  ·  F11 fullscreen\nF12 screenshot  ·  Tab fast-forward  ·  C / right stick changes field of view",10,Theme.Muted));
 }
 bool HasQuickSave()=>File.Exists(Settings.PathTo($"saves/quicksave_{settings.QuickSlot+1}.bin.0"))||File.Exists(Settings.PathTo($"saves/quicksave_{settings.QuickSlot+1}.bin.1"));
 void DisplayPage(){
  Header("Give Onett room.","Expand the scene, choose your screen size and tune the finishing effects.");
  string[] res=["1920 × 1080","2560 × 1440","3840 × 2160","3440 × 1440","1280 × 720"];
  int[] widths=[1920,2560,3840,3440,1280],heights=[1080,1440,2160,1440,720];int selected=Array.IndexOf(widths,settings.Width);if(selected<0)selected=0;
  Choice("Window resolution","Borderless fullscreen uses your monitor's current resolution.",res,selected,i=>{settings.Width=widths[i];settings.Height=heights[i];});
  Check("Borderless fullscreen","Toggle while playing with F11.",settings.Fullscreen,v=>settings.Fullscreen=v);
  Choice("Aspect ratio","Extra scenery is rendered beyond the original frame.",["Widescreen 16:9","Classic 4:3","Ultrawide 21:9"],settings.Aspect,i=>settings.Aspect=i);
  Choice("Image rendering","Scale2x softens pixel edges; Smooth uses bilinear filtering.",["Crisp pixels","Scale2x enhanced","Smooth"],settings.Filter,i=>settings.Filter=i);
  Check("Integer scaling","Use exact pixel multiples; may add bars around the image.",settings.IntegerScale,v=>settings.IntegerScale=v);
  Check("Wide field of view","Show more world scenery. C / right stick cycles the zoom.",settings.WideFov,v=>settings.WideFov=v);
  Check("Miniature depth effect","Keep the center sharp; soften the distant screen edges.",settings.TiltShift,v=>settings.TiltShift=v);
  Check("Color grading","A warmer, richer finishing pass.",settings.ColorGrading,v=>settings.ColorGrading=v);
  Check("CRT scanlines","Add a subtle alternating-row pattern.",settings.Scanlines,v=>settings.Scanlines=v);
  page.Controls.Add(Theme.Text("High-resolution output uses the game's original art with the selected effects.\nMenus and fixed artwork retain their designed framing.",10,Theme.Muted));
 }
 void AudioPage(){
  Header("A bigger sound.","MSU music replaces covered tracks while the original sound effects keep playing.");
  Check("MSU soundtrack","Use the installed fan soundtrack; missing tracks fall back to SPC audio.",settings.HqAudio,v=>settings.HqAudio=v);
  Slider("Master volume","Music and sound effects.",settings.Volume,100,v=>settings.Volume=v);
  Slider("MSU music volume","Balance the upgraded soundtrack against game sound effects.",settings.MusicVolume,100,v=>settings.MusicVolume=v);
  Section("Installed soundtrack");page.Controls.Add(Theme.Text("EarthBound MSU-1 fan pack",15));
  int count=Directory.Exists(Path.Combine(Settings.Root,"msu"))?Directory.GetFiles(Path.Combine(Settings.Root,"msu"),"*.pcm").Length:0;
  page.Controls.Add(Theme.Text($"{count} PCM tracks · 44.1 kHz stereo\nLoop points, one-shot jingles and music fades are handled natively.",11,Theme.Muted));
  Actions(Theme.Button("Install / repair soundtrack",()=>OpenSetup(true),true),Theme.Button("Open soundtrack folder",()=>Open(Path.Combine(Settings.Root,"msu"))),Theme.Button("Soundtrack credits",()=>Open(Path.Combine(Settings.Root,"CREDITS.md"))));
  page.Controls.Add(Theme.Text("To try another MSU pack, replace the PCM files in the msu folder while the game is closed. Keep a single filename prefix in that folder.",11,Theme.Muted));
 }
 void GameplayPage(){
  Header("Less friction. More adventure.","Choose the conveniences you want. Changes apply to native game logic.");
  Choice("Sprint speed","Hold Shift or the west controller button while walking.",["Off","1.5× movement","2× movement"],settings.Sprint,i=>settings.Sprint=i);
  Check("Quick dialogue","Skip character typing delays; retain scripted scene pauses.",settings.InstantText,v=>settings.InstantText=v);
  Check("Disable homesickness","Keep Ness focused without periodic homesickness rolls.",settings.NoHomesickness,v=>settings.NoHomesickness=v);
  Check("Disable Dad's reminder calls","Suppress unsolicited playtime reminders; phone saving stays available.",settings.NoDadCalls,v=>settings.NoDadCalls=v);
  Choice("Experience rewards","Affects future battles; does not alter existing levels.",["Original rewards","2× experience","3× experience","4× experience"],settings.Exp-1,i=>settings.Exp=i+1);
  Choice("Battle money","Multiply future ATM deposits earned from battles.",["Original rewards","2× money","3× money","4× money"],settings.Money-1,i=>settings.Money=i+1);
  Choice("Quick-save bank","Each bank has two crash-safe generations. F6 saves; F7 loads.",["Bank 1","Bank 2","Bank 3","Bank 4","Bank 5"],settings.QuickSlot,i=>settings.QuickSlot=i);
  Section("Built into the native engine");page.Controls.Add(Theme.Text("Save anywhere · Separate key-item storage · Party join-level fixes\nController hotplug · Left-stick movement · Fast-forward · Screenshot capture",11,Theme.Muted));
 }
 void ControlsPage(){
  Header("Your hands. Your controls.","Select a keyboard or controller binding, then press the input you want to use.");
  string[] actions=["Command menu / confirm","Cancel / status","Town map","Sprint","Talk / interact / confirm","Bicycle bell","Start / title confirm","Select / status","Move up","Move down","Move left","Move right","Fast-forward toggle","Quick save","Load quick save","Fullscreen","Pause","Screenshot","Show FPS","Open PC settings","Cycle field of view"];
  var grid=new DataGridView(){Height=400,BackgroundColor=Theme.Canvas,BorderStyle=BorderStyle.None,AllowUserToAddRows=false,AllowUserToDeleteRows=false,AllowUserToResizeRows=false,RowHeadersVisible=false,ReadOnly=true,AutoSizeColumnsMode=DataGridViewAutoSizeColumnsMode.Fill,SelectionMode=DataGridViewSelectionMode.CellSelect,MultiSelect=false,Font=Theme.Font(10),EnableHeadersVisualStyles=false,AccessibleName="Input bindings"};
  grid.DefaultCellStyle.BackColor=Theme.Canvas;grid.DefaultCellStyle.ForeColor=Theme.Ink;grid.DefaultCellStyle.SelectionBackColor=Theme.Surface;grid.DefaultCellStyle.SelectionForeColor=Theme.Gold;grid.DefaultCellStyle.Padding=new Padding(7,4,7,4);grid.GridColor=Theme.Line;grid.RowTemplate.Height=32;
  grid.ColumnHeadersDefaultCellStyle.BackColor=Theme.Rail;grid.ColumnHeadersDefaultCellStyle.ForeColor=Theme.Muted;grid.ColumnHeadersHeight=36;
  grid.Columns.Add("action","Action");grid.Columns.Add(new DataGridViewButtonColumn(){Name="key",HeaderText="Keyboard",FlatStyle=FlatStyle.Flat});grid.Columns.Add(new DataGridViewButtonColumn(){Name="pad",HeaderText="Controller",FlatStyle=FlatStyle.Flat});
  for(int i=0;i<actions.Length;i++)grid.Rows.Add(actions[i],Input.KeyName(settings.Keys[i]),Input.ButtonName(settings.Buttons[i]));
  void Bind(int row,int col){if(row<0||col<1)return;using var dialog=new BindForm(actions[row],col==2);if(dialog.ShowDialog(this)!=DialogResult.OK)return;if(col==1)settings.Keys[row]=dialog.Value;else settings.Buttons[row]=dialog.Value;grid.Rows[row].Cells[col].Value=col==1?Input.KeyName(dialog.Value):Input.ButtonName(dialog.Value);Notify("Binding changed. Apply settings to save it.");}
  grid.CellContentClick+=(_,e)=>Bind(e.RowIndex,e.ColumnIndex);grid.KeyDown+=(_,e)=>{if(e.KeyCode==Keys.Enter&&grid.CurrentCell!=null){e.Handled=true;Bind(grid.CurrentCell.RowIndex,grid.CurrentCell.ColumnIndex);}};page.Controls.Add(grid);
  Actions(Theme.Button("Reset bindings",()=>{var d=new Settings();settings.Keys=d.Keys;settings.Buttons=d.Buttons;ShowPage("Controls");Notify("Default bindings selected. Apply settings to save.");}));
  Slider("Left-stick deadzone","Percentage of travel before a direction registers.",settings.Deadzone*100/32767,90,v=>settings.Deadzone=Math.Clamp(v*32767/100,2000,30000));
  Check("Nintendo face labels","Swap south/east and west/north after applying bindings.",settings.NintendoFaceLabels,v=>settings.NintendoFaceLabels=v);
  page.Controls.Add(Theme.Text("By default: south talks, east cancels, north opens the map, west sprints.\nThe left stick moves independently of the D-pad bindings.",10,Theme.Muted));
 }
 void ModsPage(){
  Header("Make room for the extras.","Native profiles, compatible asset packs and recoverable saves.");
  Section("Native mod profiles");page.Controls.Add(Theme.Text("Profiles combine supported gameplay and visual options. Import .ebmod.json files to apply them without rebuilding the game.",11,Theme.Muted));
  Actions(Theme.Button("Import mod profile",ImportMod),Theme.Button("Export current profile",ExportMod));
  Section("Game art and data");page.Controls.Add(Theme.Text(string.IsNullOrEmpty(settings.AssetPack)?"Using your original ROM's extracted assets.":"Using asset pack: "+Path.GetFileName(settings.AssetPack),11,Theme.Muted));
  Actions(Theme.Button("Choose native .pak",ChoosePak),Theme.Button("Use original assets",()=>{settings.AssetPack="";ShowPage(current);Notify("Original assets selected. Apply to save.");}));
  page.Controls.Add(Theme.Text("A pack must match this native engine's asset layout. ROM patches (.IPS / .BPS) change SNES instructions and cannot be loaded as native mods. Full MaternalBound Redux support needs game-code ports; the research notes track that work.",10,Theme.Muted));
  Section("Saves and recovery");Actions(Theme.Button("Back up saves now",()=>BackupSession(Settings.Game)),Theme.Button("Open save folder",()=>Open(Settings.PathTo("saves"))));
  Actions(Theme.Button("Restore save backup",()=>RestoreSession(Settings.Game)));
  Actions(Theme.Button("Open backups",()=>Open(Path.Combine(Settings.User,"Backups"))),Theme.Button("Read research notes",()=>Open(Path.Combine(Settings.Root,"RESEARCH.md"))));
  page.Controls.Add(Theme.Text("A dated backup is made before every session. Quick saves are build-specific; normal in-game saves are kept separately. Copies of older backups stay available.",10,Theme.Muted));
 }
 void Try(Action action){try{action();}catch(Exception e)when(e is IOException or UnauthorizedAccessException or InvalidDataException or JsonException or ArgumentException or System.ComponentModel.Win32Exception){Notify(e.Message,true);}}
 void Open(string path){Try(()=>{if(!File.Exists(path)&&!Directory.Exists(path))throw new IOException("This file is not available yet: "+Path.GetFileName(path));Process.Start(new ProcessStartInfo(path){UseShellExecute=true});});}
 void OpenSetup(bool soundtrackOnly){if(Running){Notify("Close the game before running setup.",true);return;}using var dialog=new SetupForm(soundtrackOnly);dialog.ShowDialog(this);if(dialog.Completed){settings=Settings.Load();ShowPage(soundtrackOnly?"Audio":"Solo Play");Notify("Setup complete. Your native PC edition is ready.");}}
 void Apply(){Try(()=>{settings.Save();if(Running){File.WriteAllText(Settings.PathTo("settings.applied"),"apply");settingsRequested=false;Notify("Settings applied. Game resumed.");}else Notify("Settings saved. Ready for your next session.");});}
 void Resume(){File.WriteAllText(Settings.PathTo("settings.applied"),"resume");settingsRequested=false;}
 void Launch(bool resume,SeedRecord? seed=null){Try(()=>{
  if(Running||generating)return;
  if(seed!=null)StoryShuffle.Verify(seed);else{if(!File.Exists(settings.Pak))throw new IOException("Game data is missing. Choose a valid native asset pack.");settings.ValidatePak();}
  try {
  Settings.SessionDirectory=seed?.Session;activeSeed=seed;settings.Save();Settings.Backup(true);
  foreach(var marker in new[]{"settings.request","settings.applied"})if(File.Exists(Settings.PathTo(marker)))File.Delete(Settings.PathTo(marker));
  var p=new ProcessStartInfo(Path.Combine(Settings.BaseGame,"earthbound.exe")){WorkingDirectory=Settings.Game,UseShellExecute=false,CreateNoWindow=true};p.ArgumentList.Add("--session-dir");p.ArgumentList.Add(Settings.Game);p.ArgumentList.Add("--assets");p.ArgumentList.Add(seed?.Pak??settings.Pak);p.ArgumentList.Add("--log-file");p.ArgumentList.Add(seed==null?Path.Combine(Settings.User,"game.log"):Path.Combine(seed.Session,"game.log"));if(resume)p.ArgumentList.Add("--load-state");
  game=Process.Start(p)??throw new IOException("Game did not start.");
  }catch{Settings.SessionDirectory=null;activeSeed=null;throw;}
  Notify(seed==null?"Game running. F1 opens these settings; F9 pauses.":$"Story Shuffle running: {seed.Seed}. F1 opens settings; saves stay with this seed.");ShowPage(seed==null?"Solo Play":"Randomizer");
 });}
 void ImportMod(){using var d=new OpenFileDialog(){Filter="EarthBound profiles (*.ebmod.json)|*.ebmod.json|JSON files (*.json)|*.json"};if(d.ShowDialog(this)!=DialogResult.OK)return;Try(()=>{settings.ImportProfile(d.FileName);ShowPage(current);Notify("Profile imported. Apply settings to enable it.");});}
 void ExportMod(){using var d=new SaveFileDialog(){Filter="EarthBound profile|*.ebmod.json",FileName="My EarthBound.ebmod.json"};if(d.ShowDialog(this)!=DialogResult.OK)return;Try(()=>{var mod=new ModProfile(){Name="My EarthBound",Description="Native visual and gameplay profile"};foreach(string k in new[]{"Filter","Aspect","Scanlines","TiltShift","WideFov","ColorGrading","HqAudio","Sprint","InstantText","NoHomesickness","NoDadCalls","Exp","Money","IntegerScale"})mod.Options[k]=JsonSerializer.SerializeToElement(typeof(Settings).GetProperty(k)!.GetValue(settings));File.WriteAllText(d.FileName,JsonSerializer.Serialize(mod,Settings.JsonOptions));Notify("Profile exported.");});}
 void ChoosePak(){using var d=new OpenFileDialog(){Filter="Native EarthBound asset pack|*.pak"};if(d.ShowDialog(this)!=DialogResult.OK)return;Try(()=>{string old=settings.AssetPack;settings.AssetPack=d.FileName;try{settings.ValidatePak();}catch{settings.AssetPack=old;throw;}ShowPage(current);Notify("Compatible pack selected. Apply to save it.");});}
 void Tick(object? sender,EventArgs args){
  if(captureMode){if(captureIndex<=pages.Length+1){bool bottom=captureIndex==pages.Length+1;string name=bottom?"Randomizer":pages[captureIndex%pages.Length];if(!capturePrepared){ShowPage(name);WindowState=FormWindowState.Normal;Show();Activate();Refresh();capturePrepared=true;return;}if(bottom&&!captureScrolled){page.AutoScrollPosition=new Point(0,page.VerticalScroll.Maximum);Refresh();captureScrolled=true;return;}string root=Path.GetFullPath(Path.Combine(Settings.Root,".."));var p=new ProcessStartInfo(Path.Combine(root,"native-source",".venv","Scripts","python.exe")){UseShellExecute=false,CreateNoWindow=true};p.ArgumentList.Add(Path.Combine(root,"tools","capture_owned_window.py"));p.ArgumentList.Add(Handle.ToInt64().ToString());p.ArgumentList.Add(Path.Combine(captureDir,$"{captureIndex}-{name.Replace(" & ","-")}{(bottom?"-bottom":"")}.png"));using var capture=Process.Start(p);capture?.WaitForExit();captureIndex++;capturePrepared=captureScrolled=false;}else{captureMode=false;Close();}return;}
  if(game!=null&&game.HasExited){int code=game.ExitCode;game.Dispose();game=null;settings.ReadEngine();string log=activeSeed==null?"UserData/game.log":"this seed's Game/game.log";Settings.SessionDirectory=null;activeSeed=null;ShowPage(current);Notify(code==0?"Game closed. Your saves are stored locally.":$"The game stopped. See {log} for details.",code!=0);}
  if(Running&&File.Exists(Settings.PathTo("settings.request"))){File.Delete(Settings.PathTo("settings.request"));settings.ReadEngine();settingsRequested=true;ShowPage("Display");Show();WindowState=FormWindowState.Normal;Activate();Notify("Game paused. Apply settings to resume, or press F9 in the game.");}
 }
}
sealed class BindForm : Form {
 public int Value{get;private set;}readonly bool controller;readonly System.Windows.Forms.Timer timer=new(){Interval=25};HashSet<int> initially=[];
 public BindForm(string action,bool pad){
  controller=pad;Text="Bind "+action;ClientSize=new Size(540,245);FormBorderStyle=FormBorderStyle.FixedDialog;MaximizeBox=MinimizeBox=false;StartPosition=FormStartPosition.CenterParent;BackColor=Theme.Canvas;ForeColor=Theme.Ink;Font=Theme.Font();KeyPreview=true;
  var panel=new FlowLayoutPanel(){Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,WrapContents=false,Padding=new Padding(26)};Controls.Add(panel);panel.Controls.Add(Theme.Text(action,18));panel.Controls.Add(Theme.Text(pad?"Press a controller button or trigger.\nRelease any held buttons first.":"Press a key. Escape cancels.\nEach binding uses one physical key.",11,Theme.Muted));
  var buttons=new FlowLayoutPanel(){Width=480,Height=58};buttons.Controls.Add(Theme.Button("Clear binding",()=>Finish(pad?-1:0)));buttons.Controls.Add(Theme.Button("Cancel",()=>{DialogResult=DialogResult.Cancel;Close();}));panel.Controls.Add(buttons);
  initially=Input.Held().ToHashSet();timer.Tick+=(_,_)=>{if(!controller)return;var held=Input.Held();initially.IntersectWith(held);foreach(int b in held)if(!initially.Contains(b)){Finish(b);return;}};timer.Start();
  KeyDown+=(_,e)=>{if(e.KeyCode==Keys.Escape){DialogResult=DialogResult.Cancel;Close();}else if(!controller){int scan=Input.Scan(e.KeyCode);if(scan>0){e.Handled=e.SuppressKeyPress=true;Finish(scan);}}};FormClosed+=(_,_)=>timer.Dispose();
 }
 void Finish(int value){Value=value;DialogResult=DialogResult.OK;Close();}
}
