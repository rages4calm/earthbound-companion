// SPDX-License-Identifier: GPL-3.0-or-later
using System.Text.Json;
namespace EarthBoundCompanion;
public static class UpdatePreferences {
 static string FilePath=>Path.Combine(Settings.User,"updates.json");
 public static bool CheckOnStart {
  get{try{return JsonSerializer.Deserialize<bool>(File.ReadAllText(FilePath));}catch(Exception e)when(e is IOException or JsonException or UnauthorizedAccessException){return true;}}
  set{Directory.CreateDirectory(Settings.User);File.WriteAllText(FilePath,JsonSerializer.Serialize(value));}
 }
}
