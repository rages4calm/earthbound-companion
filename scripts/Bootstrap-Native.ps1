param([string]$Destination=(Join-Path (Split-Path $PSScriptRoot -Parent) 'native-source'))
$ErrorActionPreference='Stop'
$repoRoot=Split-Path $PSScriptRoot -Parent
$upstream='https://github.com/seanstaggsQU/earthboundRecompLinux2026.git'
$commit='76eacab54b05766b82c98da9c55d94d1236ece03'
$patches=@('native-companion.patch','native-portable.patch','native-achievements.patch','native-dialogue-camera.patch','native-render-input.patch','native-tessie-save.patch','native-palette-banks.patch', 'native-cinematic-cleanup.patch', 'native-battle-render-lifecycle.patch', 'native-text-typing.patch', 'native-cinematic-option.patch', 'native-psi-label.patch','native-paula-receipt.patch','native-npc-overlap-recovery.patch', 'native-delivery-letterbox-cleanup.patch', 'native-butterfly-spawn.patch', 'native-carpainter-letterbox.patch', 'native-passenger-bus-selection.patch', 'native-psi-tony-naming.patch', 'native-delivery-item-registers.patch')

if(Test-Path -LiteralPath $Destination){
 throw "Choose a new native-source directory. Existing checkouts are never reset: $Destination"
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
foreach($name in $patches){
 $patch=Join-Path $repoRoot "patches\$name"
 & git -C $Destination apply --check $patch
 if($LASTEXITCODE -ne 0){throw "The $name patch does not apply cleanly to the pinned source."}
 & git -C $Destination apply $patch
 if($LASTEXITCODE -ne 0){throw "Applying $name failed."}
}

Write-Output "Native source prepared at $Destination"
Write-Output "Pinned upstream: $commit"
