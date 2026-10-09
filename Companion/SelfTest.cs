using System.Text.Json;
namespace EarthBoundCompanion;
static class SelfTest {
 public static void Run(){
  var s=new Settings(){Width=-1,Height=9000,Keys=[1],Exp=500,Money=500,FastForward=500,QuickSlot=99};s.Validate();
  if(s.Width!=640||s.Height!=4320||s.Keys.Length!=21||s.Exp!=16||s.Money!=16||s.FastForward!=16||s.QuickSlot!=4)throw new Exception("Settings bounds failed");
  s.Preset("Classic");if(s.Aspect!=1||s.WideFov||s.InstantText||s.PresetIndex()!=1)throw new Exception("Classic preset failed");s.Preset("Enhanced");if(!s.WideFov||s.Filter!=1||s.Sprint!=1||s.PresetIndex()!=0)throw new Exception("Enhanced preset failed");s.NoDadCalls=true;if(s.PresetIndex()!=4)throw new Exception("Custom preset identification failed");s.NoDadCalls=false;
  foreach(var k in new[]{Keys.A,Keys.Z,Keys.Enter,Keys.F1,Keys.F12,Keys.Left,Keys.ShiftKey})if(Input.Scan(k)==0)throw new Exception("Key mapping failed "+k);
  var copy=JsonSerializer.Deserialize<Settings>(JsonSerializer.Serialize(s))!;if(copy.Keys[4]!=s.Keys[4])throw new Exception("Binding serialization failed");
  s.ShaderPreset="C:\\Shaders with spaces\\Warm.slangp";s.Validate();if(s.PresetIndex()!=4)throw new Exception("Shader custom preset identification failed");
  foreach(var bad in new[]{"preset\nvolume=0","preset\rtest","preset\0test",new string('é',512)}){var invalid=new Settings{ShaderPreset=bad};invalid.Validate();if(invalid.ShaderPreset!="")throw new Exception("Unsafe shader path accepted");}
  s.ValidatePak();
  byte[] originalAssets=File.ReadAllBytes(s.Pak);
  string report=Path.Combine(Settings.Root,"companion-selftest.txt");
  string temp=Path.Combine(Path.GetTempPath(),"EarthBoundCompanionTest-"+Guid.NewGuid());
  Settings.OverrideRoot=temp;
  try{
   Directory.CreateDirectory(Settings.Game);Directory.CreateDirectory(Settings.PathTo("saves"));File.WriteAllBytes(Settings.PathTo("saves/earthbound.srm"),[1,2,3]);
   File.WriteAllBytes(Settings.PathTo("assets.pak"),originalAssets);
   s.Exp=s.Money=16;s.FastForward=8;s.OriginalTitleScreen=true;s.Save();var loaded=Settings.Load();if(!loaded.WideFov||loaded.Filter!=1||loaded.Keys[4]!=27||loaded.Exp!=16||loaded.Money!=16||loaded.FastForward!=8||!loaded.OriginalTitleScreen)throw new Exception("Native settings persistence failed");
   string ini=File.ReadAllText(Settings.PathTo("earthbound.ini"));if(!ini.Contains("fast_forward_multiplier=8")||!ini.Contains("exp_multiplier=16")||!ini.Contains("money_multiplier=16"))throw new Exception("Playtest native INI failed");
   if(loaded.ShaderPreset!=s.ShaderPreset||!ini.Contains("shader_preset="+s.ShaderPreset))throw new Exception("Shader path persistence failed");
   loaded.Preset("Enhanced");if(loaded.ShaderPreset!="")throw new Exception("Shader preset reset failed");
   if(File.ReadAllBytes(Settings.PathTo("settings.dat")).Length!=16)throw new Exception("Engine blob size failed");
   var profile=Path.Combine(temp,"test.ebmod.json");File.WriteAllText(profile,"{\"Schema\":1,\"Name\":\"Test\",\"Options\":{\"Exp\":2,\"TiltShift\":false,\"FastForward\":16}}");loaded.ImportProfile(profile);if(loaded.Exp!=2||loaded.TiltShift||loaded.FastForward!=16)throw new Exception("Profile import failed");
   File.WriteAllText(profile,"{\"Schema\":1,\"Name\":\"Bad\",\"Options\":{\"Exp\":4,\"ArbitraryCode\":true}}");bool rejected=false;try{loaded.ImportProfile(profile);}catch(InvalidDataException){rejected=true;}if(!rejected||loaded.Exp!=2)throw new Exception("Profile rejection failed");
   string zip=Settings.Backup(true);using var archive=System.IO.Compression.ZipFile.OpenRead(zip);if(archive.GetEntry("saves/earthbound.srm")==null)throw new Exception("Save backup failed");
  }finally{Settings.OverrideRoot=null;if(temp.StartsWith(Path.GetTempPath(),StringComparison.OrdinalIgnoreCase)&&Path.GetFileName(temp).StartsWith("EarthBoundCompanionTest-"))Directory.Delete(temp,true);}
  File.WriteAllText(report,"PASS: bounds, presets, keyboard mapping, binding serialization, asset layout, native settings persistence, shader paths/reset, profile import and rejection, save backup\n");
 }
}
