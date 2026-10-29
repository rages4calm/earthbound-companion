// SPDX-License-Identifier: GPL-3.0-or-later
using System.Text.Json;
namespace EarthBoundCompanion;

static class LauncherLayoutTests {
 internal static void Run(string output) {
  output=Path.GetFullPath(output);if(Directory.Exists(output))throw new IOException("Use a fresh layout-test folder.");
  Directory.CreateDirectory(output);Settings.OverrideRoot=Path.Combine(output,"isolated-data");
  var results=new List<object>();
  foreach(float scale in new[]{1f,1.25f,1.5f,2f}) {
   using var form=new MainForm(["--layout-check"]);
   results.Add(form.VerifyLayout(scale,output));
   foreach(bool redux in new[]{false,true}) {
    using var setup=new SetupForm(reduxDevelopment:redux);setup.Show();
    setup.Scale(new SizeF(scale,scale));ScaleText(setup,scale);ResponsiveLayout.KeepOnScreen(setup);Application.DoEvents();setup.PerformLayout();
    Check(setup);Capture(setup,Path.Combine(output,$"setup-{(redux?"redux":"original")}-{scale*100:0}.png"));
    var actionButtons=Descendants(setup).OfType<Button>().Where(b=>b.Text is "Build MaternalBound Redux" or "Build my PC edition" or "Cancel").ToArray();
    if(actionButtons.Length<2||actionButtons.Any(b=>!b.Visible))throw new Exception("Setup actions hidden");
    foreach(Button button in Descendants(setup).OfType<Button>())
     if(button.Visible&&!setup.ClientRectangle.Contains(setup.RectangleToClient(button.RectangleToScreen(button.ClientRectangle))))
      throw new Exception("Setup action outside visible client area: "+button.Text);
    string fakeRom=Path.Combine(output,"invalid-fixture.sfc");File.WriteAllText(fakeRom,"synthetic invalid ROM");
    Descendants(setup).OfType<TextBox>().Single().Text=fakeRom;
    SynchronizationContext.SetSynchronizationContext(new WindowsFormsSynchronizationContext());
    Button build=actionButtons.First(b=>b.Text!="Cancel");build.Enabled=true;build.PerformClick();
    Button export=Descendants(setup).OfType<Button>().Single(b=>b.Text=="Save error report…");
    var deadline=DateTime.UtcNow.AddSeconds(5);
    while(!export.Visible&&DateTime.UtcNow<deadline){Application.DoEvents();Thread.Sleep(10);}
    if(!export.Visible||!File.ReadAllText(Path.Combine(Settings.User,"setup-diagnostics.txt")).Contains("wrong size"))throw new Exception("Setup failure did not produce an exportable report");
    Application.DoEvents();Check(setup);Capture(setup,Path.Combine(output,$"setup-error-{(redux?"redux":"original")}-{scale*100:0}.png"));
    setup.Close();
   }
  }
  File.WriteAllText(Path.Combine(output,"results.json"),JsonSerializer.Serialize(new{Passed=true,Method="Geometry and text stress at 100/125/150/200 percent with isolated data; physical system DPI unchanged",Results=results},new JsonSerializerOptions{WriteIndented=true}));
 }
 internal static void ScaleText(Control root,float factor) {
  var fonts=Descendants(root).Prepend(root).Select(c=>(Control:c,Font:c.Font)).ToArray();
  foreach(var item in fonts)item.Control.Font=new Font(item.Font.FontFamily,item.Font.Size*factor,item.Font.Style);
 }
 internal static IEnumerable<Control> Descendants(Control c){foreach(Control child in c.Controls){yield return child;foreach(var nested in Descendants(child))yield return nested;}}
 internal static void Check(Control root) {
  foreach(var c in Descendants(root).Where(c=>c.Visible)) {
   if(c is DpiComboBox combo&&combo.ItemHeight<TextRenderer.MeasureText("Ag",combo.Font).Height)throw new Exception("Clipped dropdown: "+combo.AccessibleName);
   if(c is Label l&&l.AutoSize&&l.Height<l.GetPreferredSize(new Size(Math.Max(1,l.Width),0)).Height)
    throw new Exception("Clipped label: "+l.Text);
   if(c is Button b&&b is not NavigationButton&&b.ClientSize.Width<TextRenderer.MeasureText(b.Text,b.Font).Width)
    throw new Exception("Clipped button: "+b.Text);
   if(c is TableLayoutPanel table)foreach(Control child in table.Controls)
    if(child.Visible&&child.Bottom>table.ClientSize.Height)
     throw new Exception("Clipped table cell: "+child.Text+" child="+child.Bounds+" table="+table.ClientSize+" padding="+table.Padding);
  }
 }
 internal static void Capture(Form form,string path){using var image=new Bitmap(form.Width,form.Height);form.DrawToBitmap(image,new Rectangle(Point.Empty,form.Size));image.Save(path);}
}
sealed partial class MainForm {
 internal object VerifyLayout(float scale,string output) {
  timer.Stop();Show();float before=Font.Size;Scale(new SizeF(scale,scale));ResponsiveLayout.KeepOnScreen(this);
  LauncherLayoutTests.ScaleText(nav,scale);
  foreach(string name in pages) {
   page.Font=Theme.Font();ShowPage(name);LauncherLayoutTests.ScaleText(page,scale);Application.DoEvents();ResizePage();PerformLayout();LauncherLayoutTests.Check(this);
   if(name is "Achievements" or "Game Mode" or "Display")LauncherLayoutTests.Capture(this,Path.Combine(output,$"{name}-{scale*100:0}.png"));
  }
  var result=new{Scale=scale,SystemDpi=DeviceDpi,FontBefore=before,FontAfter=Font.Size,Pages=pages.Length};Close();return result;
 }
}
