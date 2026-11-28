// SPDX-License-Identifier: GPL-3.0-or-later
// Explicit isolated release-package test mode, like Gaia's synthetic-feed test.
using System.Text.Json;
namespace EarthBoundCompanion;
public static class UpdateFixture {
 public static bool Handle(string[] args) {
  if(Environment.GetEnvironmentVariable("EB_UPDATE_FIXTURE")!="1"||!UpdateService.UsingTestFeed||!UpdateService.RelaxedHosts)return false;
  string install=UpdateService.InstallDirectory;
  if(args.Length==1&&args[0]=="--update-fixture-install") {
   var found=UpdateService.CheckAsync(install).GetAwaiter().GetResult();
   if(!found.IsNewer||found.Latest==null)throw new IOException("Fixture feed must contain a newer package.");
   string plan=UpdateService.StageAsync(install,found.Latest).GetAwaiter().GetResult();
   using var helper=UpdateService.StartHelper(plan);return true;
  }
  if(args.Length==0) {
   string? message=UpdateService.FinishPending(install);
   File.WriteAllText(Path.Combine(install,"update-fixture-result.json"),JsonSerializer.Serialize(new {Restarted=true,Version=UpdateService.CurrentVersion(install)?.ToString(),Message=message}));
   return true;
  }
  return false;
 }
}
