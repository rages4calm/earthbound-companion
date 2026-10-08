using System.Security.Cryptography;
namespace EarthBoundCompanion;

sealed partial class MainForm {
 string draftSeed=RandomNumberGenerator.GetInt32(int.MaxValue).ToString();
 ShuffleOptions draftOptions=new();string? importedBaseHash,selectedSeedId;int draftVersion=StoryShuffle.Version;
 bool generating;SeedRecord? activeSeed;
 void RandomizerPage() {
  Header("Another kind of EarthBound.","Generate a Story Shuffle adventure, choose what gets randomized, or resume a saved seed. Each seed keeps its own saves, separate from Play.");
  page.Controls.Add(Theme.Text("Keep the original story order. Change loot and wild lineups while retaining keys, quest helpers and required trade supplies.",11,Theme.Muted));
  page.Controls.Add(Theme.Text("Content-specific progression protection is always on · checked when generating and before play.",10,Theme.Green));
  var input=new TextBox {Text=draftSeed,MaxLength=80,BackColor=Theme.Surface,ForeColor=Theme.Ink,Font=Theme.Font(12),BorderStyle=BorderStyle.FixedSingle,AccessibleName="Randomizer seed",Enabled=!generating};
  input.TextChanged+=(_,_)=>{draftSeed=input.Text;importedBaseHash=null;draftVersion=StoryShuffle.Version;};
  Row("Seed","Enter a number or phrase. The same seed, options and exact game-data profile produce the same game.",input);
  void Update(ShuffleOptions options){draftOptions=options;importedBaseHash=null;draftVersion=StoryShuffle.Version;}
  Choice("Shuffle style","Balanced keeps loot near its value and lineups near their level. Surprise uses all ordinary loot and wider lineup levels.",["Balanced","Surprise"],draftOptions.Mode=="Balanced"?0:1,i=>Update(draftOptions with {Mode=i==0?"Balanced":"Surprise"}));
  var toggles=new TableLayoutPanel {ColumnCount=2,RowCount=3,Height=344,Margin=new Padding(0,8,0,4)};
  toggles.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));toggles.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));
  for(int i=0;i<3;i++)toggles.RowStyles.Add(new RowStyle(SizeType.Percent,100f/3));
  void Toggle(int column,int row,string title,string help,bool value,Action<bool> set) {
   var panel=new FlowLayoutPanel {Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,WrapContents=false,BackColor=Theme.Surface,Padding=new Padding(10),Margin=new Padding(0,0,10,8)};
   var check=new CheckBox {Text=title,Checked=value,AutoSize=true,ForeColor=Theme.Ink,Font=Theme.Font(11,FontStyle.Bold),Margin=new Padding(0,0,0,6),AccessibleName=title};check.CheckedChanged+=(_,_)=>set(check.Checked);
   var description=Theme.Text(help,10,Theme.Muted);panel.SizeChanged+=(_,_)=>description.MaximumSize=new Size(Math.Max(200,panel.Width-20),0);panel.Controls.Add(check);panel.Controls.Add(description);toggles.Controls.Add(panel,column,row);
  }
  Toggle(0,0,"Gift contents","Mix ordinary loot across item types, including money gifts and rare equipment. Keep story keys and the cave's pizza supply.",draftOptions.Gifts,v=>Update(draftOptions with {Gifts=v}));
  Toggle(1,0,"Shop stock","Mix every ordinary stock slot. Keep story keys, empty slots and Monkey Cave trade supplies. Prices stay original.",draftOptions.Shops,v=>Update(draftOptions with {Shops=v}));
  Toggle(0,1,"Enemy stats","Vary ordinary enemies by ±15% or ±30%; story battles stay fixed.",draftOptions.EnemyStats,v=>Update(draftOptions with {EnemyStats=v}));
  Toggle(1,1,"Enemy drops","Mix ordinary loot across types, including Cookie drops. Keep story drops, boss drops and original drop chances.",draftOptions.EnemyDrops,v=>Update(draftOptions with {EnemyDrops=v}));
  Toggle(0,2,"Wild encounters","Change enemy lineups in the field within level, total HP and party-size bounds. Keep scripted battles and bosses.",draftOptions.EnemyEncounters,v=>Update(draftOptions with {EnemyEncounters=v}));page.Controls.Add(toggles);
  var generate=Theme.Button(generating?"Generating…":"Generate & play",()=>GenerateDraft(true),true);
  var save=Theme.Button("Generate only",()=>GenerateDraft(false));
  var fresh=Theme.Button("New seed",()=>{draftSeed=RandomNumberGenerator.GetInt32(int.MaxValue).ToString();importedBaseHash=null;draftVersion=StoryShuffle.Version;ShowPage("Randomizer");});
  generate.Enabled=save.Enabled=fresh.Enabled=!generating&&!Running;Actions(generate,save,fresh);
  if(activeSeed!=null&&Running)page.Controls.Add(Theme.Text("Playing seed "+activeSeed.Seed+" · F1 settings apply to this session.",11,Theme.Green));
  Section("Your seed library");
  var seeds=StoryShuffle.List();
  if(File.Exists(settings.Pak)){string hash=StoryShuffle.HashFile(settings.Pak);seeds=seeds.Where(seed=>seed.BaseHash.Equals(hash,StringComparison.OrdinalIgnoreCase)).ToArray();}
  if(seeds.Count>0) {
   var list=new ComboBox {DropDownStyle=ComboBoxStyle.DropDownList,DrawMode=DrawMode.OwnerDrawFixed,ItemHeight=24,Font=Theme.Font(11),BackColor=Theme.Surface,ForeColor=Theme.Ink,AccessibleName="Saved randomizer seeds"};
   list.DrawItem+=(_,e)=>{using var brush=new SolidBrush(Theme.Surface);e.Graphics.FillRectangle(brush,e.Bounds);if(e.Index>=0)TextRenderer.DrawText(e.Graphics,list.Items[e.Index]!.ToString(),list.Font,e.Bounds,(e.State&DrawItemState.Selected)!=0?Theme.Gold:Theme.Ink,TextFormatFlags.Left|TextFormatFlags.VerticalCenter|TextFormatFlags.EndEllipsis);e.DrawFocusRectangle();};
   list.Items.AddRange(seeds.Cast<object>().ToArray());int index=Array.FindIndex(seeds.ToArray(),s=>s.Id==selectedSeedId);list.SelectedIndex=index<0?0:index;
   var info=Theme.Text("",10,Theme.Muted);SeedRecord Selected()=>(SeedRecord)list.SelectedItem!;
   void Selection(){selectedSeedId=Selected().Id;info.Text=string.Join(" · ",Selected().Changes.Select(k=>$"{k.Value} {k.Key.ToLowerInvariant()}"))+(Selected().Version<StoryShuffle.Version?" · Older seed: check safety before play. Saves are preserved.":"");}
   list.SelectedIndexChanged+=(_,_)=>Selection();Selection();page.Controls.Add(list);page.Controls.Add(info);
   var play=Theme.Button("Play selected seed",()=>Launch(false,Selected()),true);
   var resume=Theme.Button("Resume quick save",()=>Launch(true,Selected()));
   void SetResume()=>resume.Enabled=!Running&&!generating&&Enumerable.Range(0,2).Any(n=>File.Exists(Path.Combine(Selected().Session,"saves",$"quicksave_{settings.QuickSlot+1}.bin.{n}")));
   list.SelectedIndexChanged+=(_,_)=>SetResume();SetResume();play.Enabled=!Running&&!generating;Actions(play,resume);
   Actions(Theme.Button("Open seed saves",()=>Open(Path.Combine(Selected().Session,"saves"))),Theme.Button("Open spoiler log",()=>Open(Path.Combine(Selected().Folder,"spoiler.json"))),Theme.Button("Export seed recipe",()=>ExportSeedRecipe(Selected())));
   Actions(Theme.Button("Check seed safety",()=>Try(()=>{StoryShuffle.Verify(Selected());Notify("Passed: "+Selected().ContentName+" dependencies, protected sources and battle rules are intact. Full playthrough is unverified.");})),Theme.Button("Open safety report",()=>Try(()=>{string report=Path.Combine(Selected().Folder,"safety.json");if(!File.Exists(report))throw new InvalidDataException("This older seed has no generation safety report. Check seed safety before playing.");Open(report);})));
   Actions(Theme.Button("Back up seed saves",()=>BackupSession(Selected().Session)),Theme.Button("Restore seed backup",()=>RestoreSession(Selected().Session)));
   var upgrade=Theme.Button("Create v4 for selected version",()=>{draftSeed=Selected().Seed;draftOptions=Selected().Options with {EnemyEncounters=true};draftVersion=StoryShuffle.Version;importedBaseHash=Selected().BaseHash;GenerateDraft(false);});upgrade.Enabled=!Running&&!generating;Actions(upgrade);
  }else page.Controls.Add(Theme.Text("Your generated adventures will appear here. Normal-story saves stay separate.",11,Theme.Muted));
  var import=Theme.Button("Import seed recipe",ImportSeedRecipe);import.Enabled=!generating&&!Running;Actions(import,Theme.Button("Open seed library",()=>{Directory.CreateDirectory(StoryShuffle.Library);Open(StoryShuffle.Library);}));
  page.Controls.Add(Theme.Text("Story Shuffle v4 keeps the original story order while changing loot and wild encounters. It preserves keys, quest helpers and required trade sources. V3 recipes reproduce the old shuffle. Ancient Cave, Open mode, Keysanity and earthbound.app seed compatibility remain unavailable.",10,Theme.Muted));
  if(draftVersion==3)page.Controls.Add(Theme.Text("Imported v3 recipe: generation reproduces its original rules. Change an option or choose New seed to use v4.",10,Theme.Gold));
  if(generating)foreach(Control control in page.Controls)control.Enabled=false;
 }
 async void GenerateDraft(bool play) {
  if(generating||Running)return;
  string seed=draftSeed;var options=draftOptions;string? expected=importedBaseHash;int version=draftVersion;
  generating=true;ShowPage("Randomizer");Notify("Generating your adventure locally…");
  try {
   var result=await Task.Run(()=>StoryShuffle.Generate(seed,options,expected,version));selectedSeedId=result.Id;draftSeed=result.Seed;
   generating=false;ShowPage("Randomizer");Notify("Seed ready: "+result.Seed+". Its saves are separate from the normal story.");
   if(play)Launch(false,result);
  }catch(Exception e)when(e is IOException or UnauthorizedAccessException or InvalidDataException or ArgumentException or System.Text.Json.JsonException) {
   generating=false;ShowPage("Randomizer");Notify(e.Message,true);
  }
 }
 void ImportSeedRecipe() {
  using var dialog=new OpenFileDialog {Filter="Companion seed recipe (*.ebseed.json)|*.ebseed.json"};if(dialog.ShowDialog(this)!=DialogResult.OK)return;
  Try(()=>{var recipe=StoryShuffle.ImportRecipe(dialog.FileName);draftSeed=recipe.Seed;draftOptions=recipe.Options;draftVersion=recipe.Version;importedBaseHash=recipe.BaseHash;ShowPage("Randomizer");Notify("Recipe loaded. Generate it to reproduce this adventure.");});
 }
 void ExportSeedRecipe(SeedRecord seed) {
  using var dialog=new SaveFileDialog {Filter="Companion seed recipe|*.ebseed.json",FileName="EarthBound-"+seed.Id[..12]+".ebseed.json"};if(dialog.ShowDialog(this)!=DialogResult.OK)return;
  Try(()=>{File.Copy(Path.Combine(seed.Folder,"recipe.ebseed.json"),dialog.FileName,true);Notify("Recipe exported. It includes the seed and options, without game assets or saves.");});
 }
}
