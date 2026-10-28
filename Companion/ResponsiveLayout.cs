// SPDX-License-Identifier: GPL-3.0-or-later
namespace EarthBoundCompanion;

static class ResponsiveLayout {
 internal static void KeepOnScreen(Form form) {
  Rectangle area=Screen.FromControl(form).WorkingArea;
  form.MinimumSize=new Size(Math.Min(form.MinimumSize.Width,area.Width),Math.Min(form.MinimumSize.Height,area.Height));
  form.Size=new Size(Math.Min(form.Width,area.Width),Math.Min(form.Height,area.Height));
 }
 internal static void Fit(Control control,int width) {
  width=Math.Max(40,width-control.Margin.Horizontal);
  if(control is Label label){label.MaximumSize=new Size(width,0);return;}
  control.Width=width;
  if(control is TableLayoutPanel table) {
   table.AutoSize=true;table.AutoSizeMode=AutoSizeMode.GrowAndShrink;
   table.MinimumSize=new Size(width,0);table.MaximumSize=new Size(width,0);
   foreach(RowStyle row in table.RowStyles)row.SizeType=SizeType.AutoSize;
   table.PerformLayout();
   int[] columns=table.GetColumnWidths();
   foreach(Control child in table.Controls) {
    int col=table.GetColumn(child);int span=table.GetColumnSpan(child);
    int cell=columns.Skip(Math.Max(0,col)).Take(span).Sum();
    if(child is Label text)text.MaximumSize=new Size(Math.Max(40,cell-child.Margin.Horizontal-table.Padding.Horizontal),0);
    else if(child is TableLayoutPanel)Fit(child,cell);
   }
   table.PerformLayout();
  } else if(control is FlowLayoutPanel flow) {
   flow.AutoSize=true;flow.AutoSizeMode=AutoSizeMode.GrowAndShrink;
   flow.MinimumSize=new Size(width,0);flow.MaximumSize=new Size(width,0);
   if(flow.FlowDirection==FlowDirection.LeftToRight)flow.WrapContents=true;
  }
 }
}

sealed class DpiComboBox : ComboBox {
 void FitText()=>ItemHeight=Math.Max(LogicalToDeviceUnits(24),TextRenderer.MeasureText("Ag",Font).Height+LogicalToDeviceUnits(6));
 protected override void OnFontChanged(EventArgs e){base.OnFontChanged(e);FitText();}
 protected override void OnDpiChangedAfterParent(EventArgs e){base.OnDpiChangedAfterParent(e);FitText();}
}
