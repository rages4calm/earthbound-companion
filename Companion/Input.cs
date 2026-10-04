using System.Runtime.InteropServices;
namespace EarthBoundCompanion;
static class Input {
 [DllImport("kernel32",CharSet=CharSet.Unicode)]static extern bool SetDllDirectory(string path);
 [DllImport("SDL2.dll")]static extern int SDL_Init(uint flags);
 [DllImport("SDL2.dll")]static extern int SDL_NumJoysticks();
 [DllImport("SDL2.dll")]static extern int SDL_IsGameController(int index);
 [DllImport("SDL2.dll")]static extern IntPtr SDL_GameControllerOpen(int index);
 [DllImport("SDL2.dll")]static extern int SDL_GameControllerGetAttached(IntPtr controller);
 [DllImport("SDL2.dll")]static extern void SDL_GameControllerClose(IntPtr controller);
 [DllImport("SDL2.dll")]static extern byte SDL_GameControllerGetButton(IntPtr controller,int button);
 [DllImport("SDL2.dll")]static extern short SDL_GameControllerGetAxis(IntPtr controller,int axis);
 [DllImport("SDL2.dll")]static extern void SDL_GameControllerUpdate();
 [DllImport("SDL2.dll")]static extern int SDL_GetScancodeFromKey(int key);
 [DllImport("SDL2.dll")]static extern IntPtr SDL_GetScancodeName(int scan);
 [DllImport("SDL2.dll")]static extern void SDL_Quit();
 static IntPtr controller;
 public static bool Ready{get;private set;}
 public static void Init(){SetDllDirectory(Settings.Game);try{Ready=SDL_Init(0x2000)==0;}catch(DllNotFoundException){Ready=false;}}
 public static int[] Held(){
  if(!Ready)return [];SDL_GameControllerUpdate();
  if(controller!=IntPtr.Zero&&SDL_GameControllerGetAttached(controller)==0){SDL_GameControllerClose(controller);controller=IntPtr.Zero;}
  if(controller==IntPtr.Zero)for(int i=0;i<SDL_NumJoysticks();i++)if(SDL_IsGameController(i)!=0){controller=SDL_GameControllerOpen(i);break;}
  if(controller==IntPtr.Zero)return [];List<int> held=[];
  for(int i=0;i<15;i++)if(SDL_GameControllerGetButton(controller,i)!=0)held.Add(i);
  if(SDL_GameControllerGetAxis(controller,4)>16000)held.Add(15);if(SDL_GameControllerGetAxis(controller,5)>16000)held.Add(16);return held.ToArray();
 }
 public static string KeyName(int code)=>code==0?"Unbound":Ready?Marshal.PtrToStringUTF8(SDL_GetScancodeName(code))??$"Key {code}":$"Key {code}";
 public static string ButtonName(int code)=>code<0?"Unbound":new[]{"South / A / Cross","East / B / Circle","West / X / Square","North / Y / Triangle","View / Select","Guide","Start / Menu","Left stick","Right stick","Left shoulder","Right shoulder","D-pad up","D-pad down","D-pad left","D-pad right","Left trigger","Right trigger"}[Math.Clamp(code,0,16)];
 public static int Scan(Keys k){
  if(k>=System.Windows.Forms.Keys.A&&k<=System.Windows.Forms.Keys.Z)return 4+(int)k-(int)System.Windows.Forms.Keys.A;
  if(k==System.Windows.Forms.Keys.D0)return 39;
  if(k>=System.Windows.Forms.Keys.D1&&k<=System.Windows.Forms.Keys.D9)return 30+(int)k-(int)System.Windows.Forms.Keys.D1;
  if(k>=System.Windows.Forms.Keys.F1&&k<=System.Windows.Forms.Keys.F12)return 58+(int)k-(int)System.Windows.Forms.Keys.F1;
  return k switch {System.Windows.Forms.Keys.Enter=>40,System.Windows.Forms.Keys.Back=>42,System.Windows.Forms.Keys.Tab=>43,System.Windows.Forms.Keys.Space=>44,System.Windows.Forms.Keys.OemMinus=>45,System.Windows.Forms.Keys.Oemplus=>46,System.Windows.Forms.Keys.OemOpenBrackets=>47,System.Windows.Forms.Keys.OemCloseBrackets=>48,System.Windows.Forms.Keys.OemPipe=>49,System.Windows.Forms.Keys.OemSemicolon=>51,System.Windows.Forms.Keys.OemQuotes=>52,System.Windows.Forms.Keys.Oemtilde=>53,System.Windows.Forms.Keys.Oemcomma=>54,System.Windows.Forms.Keys.OemPeriod=>55,System.Windows.Forms.Keys.OemQuestion=>56,System.Windows.Forms.Keys.Insert=>73,System.Windows.Forms.Keys.Home=>74,System.Windows.Forms.Keys.PageUp=>75,System.Windows.Forms.Keys.Delete=>76,System.Windows.Forms.Keys.End=>77,System.Windows.Forms.Keys.PageDown=>78,System.Windows.Forms.Keys.Right=>79,System.Windows.Forms.Keys.Left=>80,System.Windows.Forms.Keys.Down=>81,System.Windows.Forms.Keys.Up=>82,System.Windows.Forms.Keys.ControlKey=>224,System.Windows.Forms.Keys.ShiftKey=>225,System.Windows.Forms.Keys.Menu=>226,_=>0};
 }
 public static void Quit(){if(controller!=IntPtr.Zero)SDL_GameControllerClose(controller);if(Ready)SDL_Quit();}
}
