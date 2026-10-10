// SPDX-License-Identifier: GPL-3.0-or-later
namespace EarthBoundCompanion;

internal static class HostRuntime {
#if COMPANION_PORTABLE
 internal static string? NativeLibraryDirectory;
 internal static string DataRoot => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "EarthBoundCompanionPreview");
 internal static string Executable(string name) => OperatingSystem.IsAndroid() && NativeLibraryDirectory!=null ? Path.Combine(NativeLibraryDirectory,"lib"+name+".so") : Path.Combine(AppContext.BaseDirectory, "Game", name + (OperatingSystem.IsWindows() ? ".exe" : ""));
#else
 internal static string DataRoot => AppContext.BaseDirectory;
 internal static string Executable(string name) => Path.Combine(Settings.BaseGame, name + ".exe");
#endif
}
