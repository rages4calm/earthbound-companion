using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Themes.Fluent;
namespace EarthBoundCompanion;
internal static class Program {
 [STAThread] public static void Main(string[] args) => AppBuilder.Configure<App>().UsePlatformDetect().WithInterFont().StartWithClassicDesktopLifetime(args);
}
public sealed class App : Application {
 public override void Initialize() { RequestedThemeVariant=Avalonia.Styling.ThemeVariant.Dark; Styles.Add(new FluentTheme()); }
 public override void OnFrameworkInitializationCompleted() {
  if(ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop) desktop.MainWindow=new MainWindow();
  base.OnFrameworkInitializationCompleted();
 }
}
