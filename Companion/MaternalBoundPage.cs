namespace EarthBoundCompanion;

sealed partial class MainForm {
 void MaternalBoundPage(){
  Header("MaternalBound goes native.","The project is converting MaternalBound Redux into the PC edition—not merely running its ROM patch through an emulator.");

  var statusCard=new TableLayoutPanel(){Height=88,ColumnCount=2,RowCount=1,BackColor=Theme.Surface,Padding=new Padding(18,13,18,13),Margin=new Padding(0,4,0,14)};
  statusCard.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,72));statusCard.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,28));
  var statusText=new FlowLayoutPanel(){Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,WrapContents=false,Margin=Padding.Empty};
  var statusTitle=Theme.Text("Native Redux conversion",15);statusTitle.Font=Theme.Font(15,FontStyle.Bold);statusTitle.Margin=new Padding(0,0,0,3);
  statusText.Controls.Add(statusTitle);statusText.Controls.Add(Theme.Text("Active development · v0.5",10,Theme.Muted));statusCard.Controls.Add(statusText,0,0);
  var badge=Theme.Text("PORT IN PROGRESS",10,Theme.Gold);badge.Font=Theme.Font(10,FontStyle.Bold);badge.Dock=DockStyle.Fill;badge.TextAlign=ContentAlignment.MiddleRight;badge.AutoSize=false;statusCard.Controls.Add(badge,1,0);page.Controls.Add(statusCard);

  Section("The edition we are building");
  page.Controls.Add(Theme.Text("MaternalBound Redux's restored writing, presentation and fixes · Native x64 gameplay · HD and ultrawide output · MSU music · PC controls and settings · QoL profiles · Safe randomized adventures",11));

  var stages=new TableLayoutPanel(){Height=180,ColumnCount=2,RowCount=1,Margin=new Padding(0,4,0,8)};
  stages.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));stages.ColumnStyles.Add(new ColumnStyle(SizeType.Percent,50));
  stages.Controls.Add(PortCard("WORKING NOW",Theme.Green,"Official Redux source builds locally\nNative conversion bridge and asset inventory\n190 script modules and 7,840 labels indexed\nVersioned asset, save and seed profiles\nRandomizer rejects unaudited content"),0,0);
  stages.Controls.Add(PortCard("BEING CONVERTED",Theme.Gold,"Rewritten dialogue and event scripts\nRedux graphics, data and encounter changes\n65816 assembly behavior in native C\nMaternalBound progression policy\nStart-to-ending gameplay verification"),1,0);
  page.Controls.Add(stages);

  Section("Story Shuffle v3");
  page.Controls.Add(Theme.Text("Every seed is tied to its exact game edition, asset hash, safety policy and save folder. MaternalBound generation stays locked until its native data and progression audit are complete, protecting adventures from mixed-version saves and known progression failures.",11,Theme.Muted));
  page.Controls.Add(Theme.Text("Current public test build: original EarthBound story. MaternalBound Redux gameplay will be enabled only after the native conversion and its safety checks pass.",10,Theme.Muted));
 }

 static Panel PortCard(string title,Color color,string body){
  var card=new Panel(){Dock=DockStyle.Fill,BackColor=Theme.Rail,Padding=new Padding(18,16,18,12),Margin=new Padding(0,0,10,0)};
  var stack=new FlowLayoutPanel(){Dock=DockStyle.Fill,FlowDirection=FlowDirection.TopDown,WrapContents=false,Margin=Padding.Empty};
  var heading=Theme.Text(title,10,color);heading.Font=Theme.Font(10,FontStyle.Bold);heading.Margin=new Padding(0,0,0,10);stack.Controls.Add(heading);
  var copy=Theme.Text(body,10,Theme.Muted);copy.MaximumSize=new Size(330,0);copy.Margin=Padding.Empty;stack.Controls.Add(copy);card.Controls.Add(stack);return card;
 }
}
