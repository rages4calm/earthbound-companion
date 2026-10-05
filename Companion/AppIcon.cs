namespace EarthBoundCompanion;

static class AppIcon {
 public static void Apply(Form form) {
  using var stream=typeof(AppIcon).Assembly.GetManifestResourceStream("EarthBoundCompanion.AppIcon")
   ??throw new InvalidOperationException("The application icon resource is missing.");
  using var source=new Icon(stream);
  var icon=(Icon)source.Clone();
  form.Icon=icon;
  form.Disposed+=(_,_)=>icon.Dispose();
 }
}
