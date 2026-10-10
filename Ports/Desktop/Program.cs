using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Themes.Fluent;
using Avalonia.Threading;
using Avalonia.Media.Imaging;
namespace EarthBoundCompanion;
internal static class Program {
 internal static string? SmokeOutput;
 [STAThread] public static void Main(string[] args) {
  if(args.Length==2&&args[0]=="--smoke-test"){SmokeOutput=Path.GetFullPath(args[1]);Settings.OverrideRoot=Path.Combine(Path.GetTempPath(),"eb-ui-smoke-"+Guid.NewGuid().ToString("N"));}
  AppBuilder.Configure<App>().UsePlatformDetect().WithInterFont().StartWithClassicDesktopLifetime(args);
 }
}
public sealed class App : Application {
 public override void Initialize() { RequestedThemeVariant=Avalonia.Styling.ThemeVariant.Dark; Styles.Add(new FluentTheme()); }
 public override void OnFrameworkInitializationCompleted() {
  if(ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop){
   desktop.MainWindow=new MainWindow();
   if(Program.SmokeOutput!=null){var timer=new DispatcherTimer{Interval=TimeSpan.FromSeconds(2)};timer.Tick+=(_,_)=>{timer.Stop();try{var window=desktop.MainWindow;using var bitmap=new RenderTargetBitmap(new PixelSize((int)window.Bounds.Width,(int)window.Bounds.Height),new Vector(96,96));bitmap.Render(window);bitmap.Save(Program.SmokeOutput);Console.WriteLine("Portable launcher rendered using isolated empty data.");desktop.Shutdown(0);}catch(Exception e){Console.Error.WriteLine(e);desktop.Shutdown(1);}};timer.Start();}
  }
  base.OnFrameworkInitializationCompleted();
 }
}
