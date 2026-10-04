param([string]$Destination=(Join-Path (Split-Path $PSScriptRoot -Parent) 'native-source'))
$ErrorActionPreference='Stop'
$repoRoot=Split-Path $PSScriptRoot -Parent
$upstream='https://github.com/seanstaggsQU/earthboundRecompLinux2026.git'
$commit='76eacab54b05766b82c98da9c55d94d1236ece03'
$patch=Join-Path $repoRoot 'patches\native-companion.patch'

if(Test-Path -LiteralPath $Destination){
 if(!(Test-Path -LiteralPath (Join-Path $Destination '.git'))){throw "Destination exists and is not a Git checkout: $Destination"}
 $remote=(& git -C $Destination remote get-url origin).Trim()
 if($remote -ne $upstream -and $remote -ne $upstream.Replace('.git','')){throw "Destination has an unexpected origin: $remote"}
} else {
 & git clone --recurse-submodules $upstream $Destination
 if($LASTEXITCODE -ne 0){throw 'Upstream clone failed.'}
}

& git -C $Destination fetch origin $commit
if($LASTEXITCODE -ne 0){throw 'Could not fetch the pinned upstream commit.'}
& git -C $Destination checkout --detach $commit
if($LASTEXITCODE -ne 0){throw 'Could not check out the pinned upstream commit.'}
& git -C $Destination submodule update --init --recursive
if($LASTEXITCODE -ne 0){throw 'Could not initialize upstream submodules.'}
& git -C $Destination apply --check $patch
if($LASTEXITCODE -ne 0){throw 'The Companion patch does not apply cleanly to the pinned source.'}
& git -C $Destination apply $patch
if($LASTEXITCODE -ne 0){throw 'Applying the Companion patch failed.'}

Write-Output "Native source prepared at $Destination"
Write-Output "Pinned upstream: $commit"
