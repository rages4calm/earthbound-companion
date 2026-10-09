using Avalonia.Controls;
namespace EarthBoundCompanion;
public sealed class MainWindow : Window {
 public MainWindow(){Title="EarthBound Companion · Platform Preview";Width=1020;Height=780;MinWidth=720;MinHeight=540;var view=new MainView();Content=view;Closing+=(_,e)=>{if(view.IsBusy)e.Cancel=true;};}
}
