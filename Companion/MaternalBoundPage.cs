namespace EarthBoundCompanion;

sealed partial class MainForm {
 void MaternalBoundPage(){
  Header("Choose your game mode.","Select original EarthBound or MaternalBound Redux, then continue from Play. Each edition keeps separate saves. Redux setup and conversion details are below.");

  Section("Game edition");
  var build=Theme.Button(ReduxProfileService.Ready?"Use Redux test edition":"Build Redux test edition",()=>Try(()=>{
   if(Running||generating)return;
   if(!ReduxProfileService.Ready){OpenReduxSetup();return;}
   ReduxProfileService.Select(settings);ShowPage("Play");Notify("Redux development profile selected. Its story saves and seeds stay separate.");
  }),true);build.Enabled=!Running&&!generating;build.Width=240;
  var original=Theme.Button("Use original EarthBound",()=>Try(()=>{if(Running||generating)return;settings.AssetPack="";settings.ReduxDevelopmentEnabled=false;settings.Save();ShowPage("Play");Notify("Original EarthBound selected. Its existing saves are preserved.");}));original.Enabled=!Running&&!generating;original.Width=240;Actions(build,original);

  Section("Redux development status");
  var statusCard=new TableLayoutPanel(){Height=88,ColumnCount=2,RowCount=1,BackColor=Theme.Surface,Padding=new Padding(18,13,18,13),Margin=new Padding(0,4,0,14)};
  statusCard.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,72));statusCard.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,28));
  var statusText=new FlowLayoutPanel(){Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,WrapContents=false,Margin=Padding.Empty};
  var statusTitle=Theme.Text("Native Redux conversion",15);statusTitle.Font=Theme.Font(15,FontStyle.Bold);statusTitle.Margin=new Padding(0,0,0,3);
  statusText.Controls.Add(statusTitle);statusText.Controls.Add(Theme.Text("Active development · v0.5",10,Theme.Muted));statusCard.Controls.Add(statusText,0,0);
  var badge=Theme.Text("PORT IN PROGRESS",10,Theme.Gold);badge.Font=Theme.Font(10,FontStyle.Bold);badge.Dock=DockStyle.Fill;badge.TextAlign=ContentAlignment.MiddleRight;badge.AutoSize=false;statusCard.Controls.Add(badge,1,0);page.Controls.Add(statusCard);

  Section("The edition we are building");
  page.Controls.Add(Theme.Text("MaternalBound Redux's restored writing, presentation and fixes · Native x64 gameplay · HD and ultrawide output · MSU music · PC controls and settings · QoL profiles · Safe randomized adventures",11));

  var stages=new TableLayoutPanel(){Height=210,ColumnCount=2,RowCount=1,Margin=new Padding(0,4,0,8)};
  stages.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));stages.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));
  stages.Controls.Add(PortCard("VERIFIED CHECKPOINT",Theme.Green,"7,397 converted dialogue spans\nNative shops, equipment and Jeff's Tools\nTitles, narration, cast and all 32 photos\n191 SPC tracks and 68 PSI effects\n1,000 seeds and 30 option combinations\nReproducible owner-ROM conversion"),0,0);
  stages.Controls.Add(PortCard("STILL UNDER TEST",Theme.Gold,"Complete story and randomized playthroughs\nLater event and cutscene interactions\nRemaining assembly feature audit\nEvery music transition and combat effect\nOriginal and Redux saves stay separate\nThis is a development edition"),1,0);
  page.Controls.Add(stages);

  Section("Story Shuffle v3");
  page.Controls.Add(Theme.Text("Redux's audited profile protects 110 story or trade items and 84 enemy records. Scripts, routes, bosses and required sources stay fixed. Seeds have their own saves. These checks passed; a full randomized playthrough remains unverified.",11,Theme.Muted));
  page.Controls.Add(Theme.Text("The older v0.4 preview contains original EarthBound. This source build's Redux profile is experimental and does not claim complete MaternalBound compatibility.",10,Theme.Muted));
  Section("Continue a dev.2 story");
  page.Controls.Add(Theme.Text("After building Redux in a fresh corrected-pack folder, import your dev.2 phone and quick saves here. This checked names-only upgrade preserves the old installation. It requires empty destination saves; randomized seeds keep their original edition.",10,Theme.Muted));
  var import=Theme.Button("Import dev.2 story saves",()=>Try(()=>{
   if(Running||generating)return;
   using var picker=new FolderBrowserDialog{Description="Select your previous dev.2 EarthBound Companion installation folder."};
   if(picker.ShowDialog(this)!=DialogResult.OK)return;
   int count=ReduxStoryUpgrade.Import(picker.SelectedPath);ReduxProfileService.Select(settings);ShowPage("Play");Notify($"Imported {count} story save files. Use Resume quick save to continue your F6 checkpoint.");
  }));import.Enabled=ReduxProfileService.Ready&&!Running&&!generating;import.Width=260;Actions(import);
 }

 static Panel PortCard(string title,Color color,string body){
  var card=new Panel(){Dock=DockStyle.Fill,BackColor=Theme.Rail,Padding=new Padding(18,16,18,12),Margin=new Padding(0,0,10,0)};
  var stack=new FlowLayoutPanel(){Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,WrapContents=false,Margin=Padding.Empty};
  var heading=Theme.Text(title,10,color);heading.Font=Theme.Font(10,FontStyle.Bold);heading.Margin=new Padding(0,0,0,10);stack.Controls.Add(heading);
  var copy=Theme.Text(body,10,Theme.Muted);copy.MaximumSize=new Size(330,0);copy.Margin=Padding.Empty;stack.Controls.Add(copy);card.Controls.Add(stack);return card;
 }
}
