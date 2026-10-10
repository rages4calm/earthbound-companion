using System.IO.Compression;
using System.Text;
using System.Text.Json;

namespace EarthBoundCompanion;
public sealed class Settings {
 public int Width{get;set;}=1920;public int Height{get;set;}=1080;
 public bool Fullscreen{get;set;}=true;public bool IntegerScale{get;set;}
 public int Filter{get;set;}=1;public int Aspect{get;set;}
 public string ShaderPreset{get;set;}="";
 public bool Scanlines{get;set;} public bool TiltShift{get;set;}=true;
 public bool OriginalTitleScreen{get;set;}
 public bool WideFov{get;set;}=true;public bool ColorGrading{get;set;}=true;
 public bool NintendoFaceLabels{get;set;}
 public bool HqAudio{get;set;}=true;public int Volume{get;set;}=80;public int MusicVolume{get;set;}=75;
 public int Sprint{get;set;}=1;public bool InstantText{get;set;}=true;
 public bool NoHomesickness{get;set;}=true;public bool NoDadCalls{get;set;}
 public int Exp{get;set;}=1;public int Money{get;set;}=1;public int FastForward{get;set;}=3;
 public int QuickSlot{get;set;} public int Deadzone{get;set;}=8000;
 public int[] Keys{get;set;}=[40,29,22,225,27,26,40,229,82,81,80,79,43,63,64,68,66,69,60,58,6];
 public int[] Buttons{get;set;}=[6,1,3,2,0,10,6,4,11,12,13,14,-1,-1,-1,-1,-1,-1,-1,-1,8];
 public string AssetPack{get;set;}="";
 public string ContentHash{get;set;}="";
 public bool ReduxDevelopmentEnabled{get;set;}
 static string normalContentHash="";
 internal static string? OverrideRoot;
 public static string Root=>OverrideRoot??HostRuntime.DataRoot;
 public static string? SessionDirectory;
 public static string BaseGame=>Path.Combine(Root,"Game");
 public static string Game=>SessionDirectory??(normalContentHash.Length==64?Path.Combine(User,"ContentProfiles",normalContentHash,"Game"):BaseGame);
 public static string User=>Path.Combine(Root,"UserData");
 public static string PathTo(string file)=>Path.Combine(Game,file);
 public string Pak=>string.IsNullOrEmpty(AssetPack)?Path.Combine(BaseGame,"assets.pak"):AssetPack;
 public void ConfigureContentSession(){
  if(string.IsNullOrEmpty(AssetPack)||Path.GetFullPath(Pak).Equals(Path.GetFullPath(Path.Combine(BaseGame,"assets.pak")),StringComparison.OrdinalIgnoreCase))ContentHash="";
  else if(File.Exists(Pak))ContentHash=StoryShuffle.HashFile(Pak);
  else if(ContentHash.Length!=64||!ContentHash.All(Uri.IsHexDigit))ContentHash=StoryShuffle.Hash(System.Text.Encoding.UTF8.GetBytes(Path.GetFullPath(Pak)));
  normalContentHash=ContentHash.ToLowerInvariant();
 }
 public void ValidatePak(){
  using var pack=File.OpenRead(Pak);using var reader=new BinaryReader(pack);byte[] header=reader.ReadBytes(44);
  if(header.Length!=44)throw new InvalidDataException("Asset pack header is incomplete.");
  byte[] expected=File.ReadAllBytes(Path.Combine(BaseGame,"assets.pak")).Take(44).ToArray();
  if(!header.SequenceEqual(expected))throw new InvalidDataException("This pack does not match the native engine's asset layout.");
  uint count=BitConverter.ToUInt32(header,8);
  if((ulong)pack.Length<44UL+count*8UL)throw new InvalidDataException("Asset pack index is incomplete.");
  ulong blob=(ulong)pack.Length-(44UL+count*8UL);
  for(uint i=0;i<count;i++){uint offset=reader.ReadUInt32(),size=reader.ReadUInt32();if((ulong)offset+size>blob)throw new InvalidDataException("Asset pack contains an invalid data range.");}
 }
 public static readonly JsonSerializerOptions JsonOptions=new(){WriteIndented=true};
 public static Settings Load(){
  Directory.CreateDirectory(User);Settings s;
  try {s=JsonSerializer.Deserialize<Settings>(File.ReadAllText(Path.Combine(User,"settings.json")))??new();}
  catch(IOException){s=new();}catch(JsonException){s=new();}
  s.Validate();s.ConfigureContentSession();Directory.CreateDirectory(PathTo("screenshots"));Directory.CreateDirectory(PathTo("saves"));s.ReadEngine();return s;
 }
 public void Validate(){
  ShaderPreset??="";
  if(ShaderPreset.IndexOfAny(['\r','\n','\0'])>=0||Encoding.UTF8.GetByteCount(ShaderPreset)>1023)ShaderPreset="";
  Width=Math.Clamp(Width,640,7680);Height=Math.Clamp(Height,480,4320);Filter=Math.Clamp(Filter,0,2);Aspect=Math.Clamp(Aspect,0,2);
  Volume=Math.Clamp(Volume,0,100);MusicVolume=Math.Clamp(MusicVolume,0,100);Sprint=Math.Clamp(Sprint,0,2);
  Exp=Math.Clamp(Exp,1,16);Money=Math.Clamp(Money,1,16);FastForward=Math.Clamp(FastForward,2,16);QuickSlot=Math.Clamp(QuickSlot,0,4);Deadzone=Math.Clamp(Deadzone,2000,30000);
  var defaults=new Settings();if(Keys==null||Keys.Length!=21)Keys=defaults.Keys;if(Buttons==null||Buttons.Length!=21)Buttons=defaults.Buttons;
  for(int i=0;i<21;i++){Keys[i]=Math.Clamp(Keys[i],0,511);Buttons[i]=Math.Clamp(Buttons[i],-1,16);}
 }
 public void ReadEngine(){
  if(!File.Exists(PathTo("settings.dat")))return;var b=File.ReadAllBytes(PathTo("settings.dat"));
  if(b.Length!=16||Encoding.ASCII.GetString(b,0,4)!="EBST"||b[4]!=5)return;
  Sprint=b[5];HqAudio=b[6]!=0;NintendoFaceLabels=b[7]!=0;Scanlines=b[9]!=0;if(b[10]!=0)Filter=1;else if(Filter==1)Filter=0;
  TiltShift=b[11]!=0;WideFov=b[12]!=0;ColorGrading=b[13]!=0;Aspect=b[14];Validate();
 }
 static void Atomic(string file,byte[] data){File.WriteAllBytes(file+".tmp",data);File.Move(file+".tmp",file,true);}
 public void Save(){
  Validate();ConfigureContentSession();Directory.CreateDirectory(User);Directory.CreateDirectory(Game);Directory.CreateDirectory(PathTo("screenshots"));
  Backup(false);Atomic(Path.Combine(User,"settings.json"),JsonSerializer.SerializeToUtf8Bytes(this,JsonOptions));
  WriteEngine(BaseGame);if(!Game.Equals(BaseGame,StringComparison.OrdinalIgnoreCase))WriteEngine(Game);
 }
 public void WriteEngine(string directory){
  Directory.CreateDirectory(directory);Directory.CreateDirectory(Path.Combine(directory,"saves"));Directory.CreateDirectory(Path.Combine(directory,"screenshots"));
  byte[] b=new byte[16];Encoding.ASCII.GetBytes("EBST").CopyTo(b,0);b[4]=5;b[5]=(byte)Sprint;b[6]=(byte)(HqAudio?1:0);
  b[7]=(byte)(NintendoFaceLabels?1:0);
  b[9]=(byte)(Scanlines?1:0);b[10]=(byte)(Filter==1?1:0);b[11]=(byte)(TiltShift?1:0);b[12]=(byte)(WideFov?1:0);b[13]=(byte)(ColorGrading?1:0);b[14]=(byte)Aspect;
  Atomic(Path.Combine(directory,"settings.dat"),b);
  var ini=new StringBuilder($"# Managed by EarthBound Companion\ncompanion=1\nwidth={Width}\nheight={Height}\nfullscreen={(Fullscreen?1:0)}\ninteger_scale={(IntegerScale?1:0)}\nfilter={Filter}\nvolume={Volume}\nmusic_volume={MusicVolume}\ninstant_text={(InstantText?1:0)}\nno_homesickness={(NoHomesickness?1:0)}\nno_dad_calls={(NoDadCalls?1:0)}\nexp_multiplier={Exp}\nmoney_multiplier={Money}\nfast_forward_multiplier={FastForward}\nquick_slot={QuickSlot}\ndeadzone={Deadzone}\nmsu_dir={Path.GetFullPath(Path.Combine(Root,"msu"))}\n");
  ini.AppendLine($"shader_preset={ShaderPreset}");
  for(int i=0;i<21;i++)ini.AppendLine($"key.{i}={Keys[i]}\nbutton.{i}={Buttons[i]}");
  Atomic(Path.Combine(directory,"earthbound.ini"),Encoding.UTF8.GetBytes(ini.ToString()));
 }
 public static string Backup(bool saves,string? session=null){
  session=Path.GetFullPath(session??Game);
  string dir=Path.Combine(User,"Backups");Directory.CreateDirectory(dir);
  string path=Path.Combine(dir,(saves?"session-":"settings-")+DateTime.Now.ToString("yyyyMMdd-HHmmss-fff")+"-"+Guid.NewGuid().ToString("N")[..8]+".zip");
  using(var zip=ZipFile.Open(path,ZipArchiveMode.Create)){
   using(var writer=new StreamWriter(zip.CreateEntry("session.txt").Open()))writer.WriteLine(session);
   foreach(string f in new[]{"settings.dat","earthbound.ini"})if(File.Exists(Path.Combine(session,f)))zip.CreateEntryFromFile(Path.Combine(session,f),f);
   if(File.Exists(Path.Combine(User,"settings.json")))zip.CreateEntryFromFile(Path.Combine(User,"settings.json"),"settings.json");
   if(saves){using(var writer=new StreamWriter(zip.CreateEntry("save-manifest.json").Open()))writer.Write(JsonSerializer.Serialize(SaveRecovery.Snapshot(session),JsonOptions));}
   if(saves&&Directory.Exists(Path.Combine(session,"saves")))foreach(var f in Directory.GetFiles(Path.Combine(session,"saves")))zip.CreateEntryFromFile(f,"saves/"+Path.GetFileName(f));
  }
  return path;
 }
 public void Preset(string name){
  var fresh=new Settings();if(name=="Classic"){fresh.Aspect=1;fresh.Filter=0;fresh.TiltShift=fresh.WideFov=fresh.ColorGrading=fresh.HqAudio=fresh.InstantText=fresh.NoHomesickness=false;fresh.Sprint=0;fresh.IntegerScale=true;}
  if(name=="CRT"){fresh.Scanlines=true;fresh.Filter=0;fresh.TiltShift=false;fresh.IntegerScale=true;}
  if(name=="Easygoing"){fresh.Exp=fresh.Money=2;fresh.Sprint=2;fresh.NoDadCalls=true;}
  Width=fresh.Width;Height=fresh.Height;Fullscreen=fresh.Fullscreen;IntegerScale=fresh.IntegerScale;Filter=fresh.Filter;Aspect=fresh.Aspect;
  ShaderPreset="";
  Scanlines=fresh.Scanlines;TiltShift=fresh.TiltShift;WideFov=fresh.WideFov;ColorGrading=fresh.ColorGrading;HqAudio=fresh.HqAudio;
  Sprint=fresh.Sprint;InstantText=fresh.InstantText;NoHomesickness=fresh.NoHomesickness;NoDadCalls=fresh.NoDadCalls;Exp=fresh.Exp;Money=fresh.Money;FastForward=fresh.FastForward;
 }
 public int PresetIndex(){
  string[] props=["IntegerScale","Filter","Aspect","Scanlines","TiltShift","WideFov","ColorGrading","HqAudio","Sprint","InstantText","NoHomesickness","NoDadCalls","Exp","Money","FastForward"];
  if(ShaderPreset.Length>0)return 4;
  string[] names=["Enhanced","Classic","CRT","Easygoing"];
  for(int i=0;i<names.Length;i++){var candidate=new Settings();candidate.Preset(names[i]);if(props.All(p=>Equals(typeof(Settings).GetProperty(p)!.GetValue(this),typeof(Settings).GetProperty(p)!.GetValue(candidate))))return i;}
  return 4;
 }
 public void ImportProfile(string path){
  var mod=JsonSerializer.Deserialize<ModProfile>(File.ReadAllText(path))??throw new InvalidDataException("Empty profile.");
  if(mod.Schema!=1||string.IsNullOrWhiteSpace(mod.Name)||mod.Options==null)throw new InvalidDataException("Use an EarthBound Companion schema 1 profile.");
  var allowed=new HashSet<string>(["Filter","Aspect","Scanlines","TiltShift","WideFov","ColorGrading","OriginalTitleScreen","HqAudio","Sprint","InstantText","NoHomesickness","NoDadCalls","Exp","Money","FastForward","IntegerScale"]);
  var copy=JsonSerializer.Deserialize<Settings>(JsonSerializer.Serialize(this))!;
  foreach(var (key,value) in mod.Options){if(!allowed.Contains(key))throw new InvalidDataException($"Unsupported option: {key}");var p=typeof(Settings).GetProperty(key)!;p.SetValue(copy,value.Deserialize(p.PropertyType));}
  copy.Validate();foreach(var key in mod.Options.Keys)typeof(Settings).GetProperty(key)!.SetValue(this,typeof(Settings).GetProperty(key)!.GetValue(copy));
  Directory.CreateDirectory(Path.Combine(User,"Mods"));File.WriteAllText(Path.Combine(User,"Mods",Guid.NewGuid()+".ebmod.json"),JsonSerializer.Serialize(mod,JsonOptions));
 }
}
public sealed class ModProfile{public int Schema{get;set;}=1;public string Name{get;set;}="";public string Description{get;set;}="";public Dictionary<string,JsonElement> Options{get;set;}=new();}
