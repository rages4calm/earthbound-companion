// SPDX-License-Identifier: GPL-3.0-or-later
// SemVer and verified GitHub downloads adapted from our Illusion of Gaia updater.
using System.Diagnostics;
using System.Formats.Tar;
using System.IO.Compression;
using System.Net;
using System.Net.Http.Headers;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
namespace EarthBoundCompanion;
public sealed class ReleaseVersion : IComparable<ReleaseVersion>, IEquatable<ReleaseVersion>
{
    private static readonly Regex Pattern = new(@"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+[0-9A-Za-z.-]+)?$", RegexOptions.CultureInvariant);
    public int Major { get; } public int Minor { get; } public int Patch { get; }
    public IReadOnlyList<string> Prerelease { get; }
    private ReleaseVersion(int major, int minor, int patch, string[] pre) { Major = major; Minor = minor; Patch = patch; Prerelease = pre; }

    public static bool TryParse(string? text, out ReleaseVersion version)
    {
        version = null!;
        var match = Pattern.Match(text?.Trim() ?? "");
        if (!match.Success || !int.TryParse(match.Groups[1].Value, out var a) || !int.TryParse(match.Groups[2].Value, out var b) || !int.TryParse(match.Groups[3].Value, out var c)) return false;
        var pre = match.Groups[4].Success ? match.Groups[4].Value.Split('.') : Array.Empty<string>();
        if (pre.Any(id => id.Length > 1 && id[0] == '0' && id.All(char.IsAsciiDigit))) return false;   // no leading zeros in numeric identifiers
        version = new ReleaseVersion(a, b, c, pre); return true;
    }
    public static ReleaseVersion Parse(string text) => TryParse(text, out var v) ? v : throw new FormatException("Not a release version: " + text);

    public int CompareTo(ReleaseVersion? other)
    {
        if (other is null) return 1;
        int core = Major != other.Major ? Major.CompareTo(other.Major) : Minor != other.Minor ? Minor.CompareTo(other.Minor) : Patch.CompareTo(other.Patch);
        if (core != 0) return core;
        if (Prerelease.Count == 0 || other.Prerelease.Count == 0)   // a release outranks its own pre-releases
            return Prerelease.Count == other.Prerelease.Count ? 0 : Prerelease.Count == 0 ? 1 : -1;
        for (int i = 0; i < Math.Min(Prerelease.Count, other.Prerelease.Count); i++) {
            string x = Prerelease[i], y = other.Prerelease[i];
            bool xn = x.All(char.IsAsciiDigit), yn = y.All(char.IsAsciiDigit);
            int step = xn && yn ? (x.Length != y.Length ? x.Length.CompareTo(y.Length) : string.CompareOrdinal(x, y))
                : xn ? -1 : yn ? 1 : string.CompareOrdinal(x, y);
            if (step != 0) return Math.Sign(step);
        }
        return Prerelease.Count.CompareTo(other.Prerelease.Count);
    }
    public bool Equals(ReleaseVersion? other) => CompareTo(other) == 0;
    public override bool Equals(object? obj) => obj is ReleaseVersion v && Equals(v);
    public override int GetHashCode() => ToString().GetHashCode();
    public override string ToString() => $"{Major}.{Minor}.{Patch}" + (Prerelease.Count == 0 ? "" : "-" + string.Join('.', Prerelease));
    /// <summary>"beta 22" for 0.2.0-beta.22, otherwise the full version.</summary>
    public string ShortLabel => Prerelease.Count == 2 && Prerelease[1].All(char.IsAsciiDigit) ? $"{Prerelease[0]} {Prerelease[1]}" : ToString();
    public static bool operator >(ReleaseVersion a, ReleaseVersion b) => a.CompareTo(b) > 0;
    public static bool operator <(ReleaseVersion a, ReleaseVersion b) => a.CompareTo(b) < 0;
}


public sealed record UpdateAsset(string Name, Uri Url, long Size, string? Sha256);
public sealed record UpdateRelease(ReleaseVersion Version, string Tag, string Title, string Notes, UpdateAsset Zip, UpdateAsset? ChecksumFile, Uri? Page);
public sealed record UpdateCheck(ReleaseVersion? Current, UpdateRelease? Latest) {
    public bool IsNewer => Latest != null && (Current == null || Latest.Version > Current);
}
public sealed record UpdateProgress(string Phase, long Done, long Total);
public sealed class UpdateException : IOException {
    public UpdateException(string message, Exception? inner = null) : base(message, inner) { }
}
public static partial class UpdateService {
    public const string DefaultFeed = "https://api.github.com/repos/rages4calm/earthbound-companion/releases?per_page=50";
    public const string FeedVariable = "EB_UPDATE_FEED";
    const string UserAgent = "EarthBoundCompanion-Updater";
    const long MaxPackageBytes = 2L << 30;
    public static Action<Uri, Uri?, int>? Trace;
    public static bool UsingTestFeed => !string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(FeedVariable));
    public static bool RelaxedHosts => UsingTestFeed && !(Uri.TryCreate(Environment.GetEnvironmentVariable(FeedVariable), UriKind.Absolute, out var feed)
        && feed.Scheme == Uri.UriSchemeHttps && feed.IsDefaultPort && feed.Host == "api.github.com");
    public static string Platform => OperatingSystem.IsAndroid() ? (RuntimeInformation.ProcessArchitecture == Architecture.Arm64 ? "android-arm64" : "android-x64")
        : OperatingSystem.IsWindows() ? "win-x64" : OperatingSystem.IsMacOS() ? (RuntimeInformation.ProcessArchitecture == Architecture.Arm64 ? "osx-arm64" : "osx-x64") : "linux-x64";
    public static string LauncherRelative => Platform == "win-x64" ? "EarthBound Companion.exe" : Platform.StartsWith("osx-") ? "Contents/MacOS/EarthBoundCompanion.Portable" : "EarthBoundCompanion.Portable";
    public static string EngineRelative => Platform == "win-x64" ? "Game/earthbound.exe" : Platform.StartsWith("osx-") ? "Contents/MacOS/Game/earthbound" : "Game/earthbound";
    public static string InstallDirectory {
        get {
            var app = Path.GetFullPath(AppContext.BaseDirectory).TrimEnd(Path.DirectorySeparatorChar);
            return Platform.StartsWith("osx-") ? Path.GetFullPath(Path.Combine(app, "../..")) : app;
        }
    }
    public static ReleaseVersion? CurrentVersion(string directory) {
        var stamp = typeof(UpdateService).Assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion;
        return ReleaseVersion.TryParse(stamp, out var version) ? version : null;
    }
    public static UpdateRelease? PickLatest(string json, string? platform = null) {
        platform ??= Platform;
        using var doc = JsonDocument.Parse(json);
        if(doc.RootElement.ValueKind != JsonValueKind.Array) throw new UpdateException("GitHub returned an unreadable release list.");
        UpdateRelease? best = null;
        foreach(var r in doc.RootElement.EnumerateArray()) {
            if(Bool(r,"draft")) continue;
            string tag=Text(r,"tag_name");
            if(!ReleaseVersion.TryParse(tag,out var v)) continue;
            if(platform=="win-x64" && (Bool(r,"prerelease") || v.Prerelease.Count != 0)) continue;
            string expected=platform=="win-x64" ? $"EarthBound-Companion-Windows-v{v}.zip" : $"EarthBound-Companion-{platform}-preview."+(platform.StartsWith("android-")?"apk":"tar.gz");
            UpdateAsset? package=null, sums=null;
            if(r.TryGetProperty("assets",out var assets)) foreach(var a in assets.EnumerateArray()) {
                string name=Text(a,"name");if(name!=expected&&name!=expected+".sha256") continue;
                if(!Uri.TryCreate(Text(a,"browser_download_url"),UriKind.Absolute,out var url)) continue;
                string digest=Text(a,"digest"); string? sha=digest.StartsWith("sha256:")&&Regex.IsMatch(digest[7..],"^[0-9a-fA-F]{64}$")?digest[7..].ToLowerInvariant():null;
                var asset=new UpdateAsset(name,url,a.TryGetProperty("size",out var size)?size.GetInt64():0,sha);
                if(name==expected)package=asset;else sums=asset;
            }
            if(package==null || (best!=null && v.CompareTo(best.Version)<=0))continue;
            Uri.TryCreate(Text(r,"html_url"),UriKind.Absolute,out var page);
            best=new(v,tag,Text(r,"name"),PlainText(Text(r,"body")),package,sums,page);
        }
        return best;
    }
    static string Text(JsonElement e,string name)=>e.TryGetProperty(name,out var v)&&v.ValueKind==JsonValueKind.String?v.GetString()??"":"";
    static bool Bool(JsonElement e,string name)=>e.TryGetProperty(name,out var v)&&v.ValueKind==JsonValueKind.True;
    static void TryDelete(string path){try{File.Delete(path);}catch(IOException){}catch(UnauthorizedAccessException){}}
    public static string PlainText(string markdown)
    {
        var text = markdown.Replace("\r\n", "\n");
        text = Regex.Replace(text, @"!\[([^\]]*)\]\([^)]*\)", "$1");
        text = Regex.Replace(text, @"\[([^\]]+)\]\(([^)\s]+)\)", "$1");
        text = Regex.Replace(text, @"(?m)^#{1,6}[ \t]+", "");
        text = Regex.Replace(text, @"(\*\*|__)(.+?)\1", "$2");
        text = Regex.Replace(text, @"(?m)^([ \t]*)[*+][ \t]+", "$1- ");
        text = text.Replace("`", "");
        text = Regex.Replace(text, @"<[^>\n]+>", "");
        text = Regex.Replace(text, @"\n{3,}", "\n\n");
        return text.Trim().Replace("\n", "\r\n");
    }

    public static HttpClient CreateClient()
    {
        var handler = new HttpClientHandler { AllowAutoRedirect = true, MaxAutomaticRedirections = 5, UseCookies = false, CheckCertificateRevocationList = false };
        var client = new HttpClient(handler) { Timeout = Timeout.InfiniteTimeSpan };
        client.DefaultRequestHeaders.UserAgent.Add(new ProductInfoHeaderValue(UserAgent, "1"));
        return client;
    }

    /// <summary>Only HTTPS to GitHub. A test feed may also use plain HTTP on this computer (loopback).</summary>
    public static void RequireAllowed(Uri url)
    {
        if (url.Scheme == Uri.UriSchemeHttps) {
            var host = url.Host.ToLowerInvariant();
            if (RelaxedHosts) return;
            if (url.IsDefaultPort && (host is "api.github.com" or "github.com" || host.EndsWith(".githubusercontent.com", StringComparison.Ordinal))) return;
        }
        if (RelaxedHosts && url.Scheme == Uri.UriSchemeHttp && url.IsLoopback) return;
        throw new UpdateException($"Refused to download from {url.Scheme}://{url.Host}: updates only come over HTTPS from GitHub.");
    }

    public static async Task<UpdateCheck> CheckAsync(string installDirectory, HttpClient? client = null, CancellationToken cancel = default)
    {
        var current = CurrentVersion(installDirectory);
        var feed = Environment.GetEnvironmentVariable(FeedVariable);
        string json;
        if (!string.IsNullOrWhiteSpace(feed) && !feed.Contains("://")) json = await File.ReadAllTextAsync(feed, cancel).ConfigureAwait(false);
        else {
            var url = new Uri(string.IsNullOrWhiteSpace(feed) ? DefaultFeed : feed);
            RequireAllowed(url);
            var owned = client == null; client ??= CreateClient();
            try {
                using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancel); timeout.CancelAfter(TimeSpan.FromSeconds(20));
                using var request = new HttpRequestMessage(HttpMethod.Get, url);
                request.Headers.Accept.ParseAdd("application/vnd.github+json"); request.Headers.Add("X-GitHub-Api-Version", "2022-11-28");
                using var response = await Send(client, request, timeout.Token, cancel).ConfigureAwait(false);
                await RequireSuccess(response).ConfigureAwait(false);
                json = await response.Content.ReadAsStringAsync(timeout.Token).ConfigureAwait(false);
            } finally { if (owned) client.Dispose(); }
        }
        try { return new(current, PickLatest(json)); }
        catch (JsonException error) { throw new UpdateException("The release list could not be read. Try again later.", error); }
    }

    private static async Task<HttpResponseMessage> Send(HttpClient client, HttpRequestMessage request, CancellationToken token, CancellationToken player)
    {
        var requested = request.RequestUri!;   // HttpClient rewrites RequestUri when it follows a redirect
        try {
            var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, token).ConfigureAwait(false);
            Trace?.Invoke(requested, response.RequestMessage?.RequestUri, (int)response.StatusCode);
            if (response.RequestMessage?.RequestUri is { } final) RequireAllowed(final);
            return response;
        } catch (OperationCanceledException) when (!player.IsCancellationRequested) {
            throw new UpdateException("GitHub did not answer in time. Check your internet connection and try again.");
        } catch (HttpRequestException error) {
            throw new UpdateException("Could not reach GitHub. Check your internet connection and try again.", error);
        }
    }

    private static async Task RequireSuccess(HttpResponseMessage response)
    {
        if (response.IsSuccessStatusCode) return;
        var limited = response.Headers.TryGetValues("X-RateLimit-Remaining", out var left) && left.FirstOrDefault() == "0";
        if (limited || response.StatusCode == (HttpStatusCode)429) {
            var when = response.Headers.TryGetValues("X-RateLimit-Reset", out var reset) && long.TryParse(reset.FirstOrDefault(), out var epoch)
                ? " after " + DateTimeOffset.FromUnixTimeSeconds(epoch).ToLocalTime().ToString("t") : " in a little while";
            throw new UpdateException($"GitHub is limiting update checks from this network right now. Try again{when}.");
        }
        await Task.CompletedTask;
        throw new UpdateException($"GitHub answered {(int)response.StatusCode} {response.ReasonPhrase}. Try again later.");
    }

    // ---------- download and verification ----------

    /// <summary>Downloads the zip and refuses it unless it matches every checksum GitHub publishes for it.</summary>
    public static async Task<string> DownloadAsync(UpdateRelease release, string destination, IProgress<UpdateProgress>? progress = null, HttpClient? client = null, CancellationToken cancel = default)
    {
        var owned = client == null; client ??= CreateClient();
        try {
            string? published = null;
            if (release.ChecksumFile != null) {
                RequireAllowed(release.ChecksumFile.Url);
                using var request = new HttpRequestMessage(HttpMethod.Get, release.ChecksumFile.Url);
                using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancel); timeout.CancelAfter(TimeSpan.FromSeconds(30));
                using var response = await Send(client, request, timeout.Token, cancel).ConfigureAwait(false);
                await RequireSuccess(response).ConfigureAwait(false);
                published = ParseChecksumFile(await response.Content.ReadAsStringAsync(timeout.Token).ConfigureAwait(false), release.Zip.Name);
            }
            if (release.Zip.Sha256 == null && published == null)
                throw new UpdateException("This release has no published checksum, so the download cannot be verified. It was not installed.");
            if (release.Zip.Sha256 != null && published != null && release.Zip.Sha256 != published)
                throw new UpdateException("The release's two published checksums disagree. Nothing was installed; please report this.");

            RequireAllowed(release.Zip.Url);
            string actual;
            var partial = destination + ".partial";
            try {
                using var request = new HttpRequestMessage(HttpMethod.Get, release.Zip.Url);
                request.Headers.Accept.ParseAdd("application/octet-stream");
                using var timeout = CancellationTokenSource.CreateLinkedTokenSource(cancel); timeout.CancelAfter(TimeSpan.FromMinutes(30));
                using var response = await Send(client, request, timeout.Token, cancel).ConfigureAwait(false);
                await RequireSuccess(response).ConfigureAwait(false);
                var total = response.Content.Headers.ContentLength ?? release.Zip.Size;
                if (total > MaxPackageBytes) throw new UpdateException("The download is far larger than a Companion build. It was refused.");
                using var hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
                await using (var input = await response.Content.ReadAsStreamAsync(timeout.Token).ConfigureAwait(false))
                await using (var output = new FileStream(partial, FileMode.CreateNew, FileAccess.Write, FileShare.None, 1 << 16, true)) {
                    var buffer = new byte[1 << 16]; long done = 0; int read;
                    while ((read = await input.ReadAsync(buffer, timeout.Token).ConfigureAwait(false)) > 0) {
                        hash.AppendData(buffer, 0, read); await output.WriteAsync(buffer.AsMemory(0, read), timeout.Token).ConfigureAwait(false);
                        done += read; if (done > MaxPackageBytes) throw new UpdateException("The download is far larger than a Companion build. It was refused.");
                        progress?.Report(new("Downloading", done, total));
                    }
                    await output.FlushAsync(timeout.Token).ConfigureAwait(false);
                }
                actual = Convert.ToHexString(hash.GetHashAndReset()).ToLowerInvariant();
            } catch (OperationCanceledException) when (!cancel.IsCancellationRequested) {
                throw new UpdateException("The download stalled. Check your connection and try again.");
            } catch (IOException error) {
                throw new UpdateException("The download was interrupted: " + error.Message, error);
            } catch (HttpRequestException error) {
                throw new UpdateException("The download was interrupted. Check your connection and try again.", error);
            }
            var expected = release.Zip.Sha256 ?? published!;
            if (!string.Equals(actual, expected, StringComparison.Ordinal)) {
                TryDelete(partial);
                throw new UpdateException($"The download does not match its published checksum (expected {expected[..12]}…, got {actual[..12]}…). It was deleted and nothing was installed.");
            }
            File.Move(partial, destination, false);
            return actual;
        } finally { if (owned) client.Dispose(); TryDelete(destination + ".partial"); }
    }

    /// <summary>Reads "&lt;hex&gt; *name" (sha256sum) or a bare hash.</summary>
    public static string ParseChecksumFile(string text, string zipName)
    {
        foreach (var line in text.Split('\n').Select(x => x.Trim()).Where(x => x.Length > 0)) {
            var match = Regex.Match(line, @"^([0-9a-fA-F]{64})(?:\s+\*?(.+))?$");
            if (match.Success && (!match.Groups[2].Success || match.Groups[2].Value.Trim() == zipName)) return match.Groups[1].Value.ToLowerInvariant();
        }
        throw new UpdateException("The release's .sha256 file could not be read, so the download cannot be verified.");
    }

}
