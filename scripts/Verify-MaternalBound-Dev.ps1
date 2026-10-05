param(
 [Parameter(Mandatory=$true)][string]$NativeExe,
 [Parameter(Mandatory=$true)][string]$BaseAssets,
 [Parameter(Mandatory=$true)][string]$ConvertedDirectory,
 [Parameter(Mandatory=$true)][string]$Bridge,
 [Parameter(Mandatory=$true)][string]$ScratchDirectory
)
$ErrorActionPreference='Stop'
$NativeExe=(Resolve-Path -LiteralPath $NativeExe).Path
$BaseAssets=(Resolve-Path -LiteralPath $BaseAssets).Path
$ConvertedDirectory=(Resolve-Path -LiteralPath $ConvertedDirectory).Path
$inventory=Get-Content -LiteralPath $Bridge -Raw | ConvertFrom-Json
$relocations=Get-Content -LiteralPath (Join-Path $ConvertedDirectory 'dialogue-relocations.json') -Raw | ConvertFrom-Json
$report=Get-Content -LiteralPath (Join-Path $ConvertedDirectory 'dialogue-report.json') -Raw | ConvertFrom-Json
$blob=Join-Path $ConvertedDirectory 'dialogue.bin'
if((Get-FileHash -LiteralPath $blob -Algorithm SHA256).Hash -ne $report.blobSha256 -or $report.blobSha256 -ne $relocations.blobSha256){throw 'Dialogue files do not match the conversion report.'}
New-Item -ItemType Directory -Path $ScratchDirectory -Force | Out-Null
$ScratchDirectory=(Resolve-Path -LiteralPath $ScratchDirectory).Path
$results=@()
$common='--assets "'+$BaseAssets+'" --session-dir "'+$ScratchDirectory+'" --save "'+(Join-Path $ScratchDirectory 'dev-test.srm')+'" '
function Invoke-NativeCheck([string]$Name,[string]$Arguments){
 $stderr=Join-Path $ScratchDirectory ($Name+'.log')
 $stdout=Join-Path $ScratchDirectory ($Name+'.out')
 $process=Start-Process -FilePath $NativeExe -ArgumentList ($common+$Arguments) -WindowStyle Hidden -Wait -PassThru -RedirectStandardError $stderr -RedirectStandardOutput $stdout
 Get-Content -LiteralPath $stderr
 if($process.ExitCode -ne 0){throw "Native check failed: $Name, exit $($process.ExitCode)"}
}
Invoke-NativeCheck 'redux-vm' '--selftest-redux-vm'
$vmLog=Get-Content -LiteralPath (Join-Path $ScratchDirectory 'redux-vm.log') -Raw
if($vmLog -notmatch 'Redux VM native command checks: (\d+), PASS'){throw 'Native command check did not report a passing count.'}
$results+=@{test='native-redux-commands';checks=[int]$Matches[1];exitCode=0}
if($vmLog -match 'Redux stamina depletion/recovery checks: PASS'){
 $results+=@{test='native-redux-stamina';exitCode=0}
}
Invoke-NativeCheck 'redux-ai' '--selftest-redux-ai'
$aiLog=Get-Content -LiteralPath (Join-Path $ScratchDirectory 'redux-ai.log') -Raw
if($aiLog -notmatch 'Redux enemy AI checks: (\d+) scripts, (\d+) turns, PASS'){throw 'Native enemy AI check did not pass.'}
$results+=@{test='native-redux-enemy-ai';scripts=[int]$Matches[1];turns=[int]$Matches[2];exitCode=0}
Invoke-NativeCheck 'redux-names' '--selftest-redux-names'
$results+=@{test='native-redux-names-food-phone-save-migration';exitCode=0}
Invoke-NativeCheck 'redux-motion' '--selftest-redux-motion'
$results+=@{test='native-redux-animation-run-exhaustion-stationary-stamina';exitCode=0}
Invoke-NativeCheck 'redux-movement' '--selftest-redux-movement'
$movementLog=Get-Content -LiteralPath (Join-Path $ScratchDirectory 'redux-movement.log') -Raw
foreach($required in @('all 898 nonzero entries resolve, PASS','compiled completion writes, invisible controller and DMA-empty wait, PASS','real relocated hook, resting frame and return, PASS','65536 speeds, 50 unsigned comparisons, distance/frame and original fade entry, PASS','resumable fade-in finishes at full brightness without leftover mosaic, PASS','22-slot exhaustion, reserved party slots and released-slot reuse, PASS','128 distant-NPC allocation cycles','16 leader, revival, KO and mushroom refresh cases','6 map-boundary rejects, 8 interrupted-stair callbacks')) {
 if(!$movementLog.Contains($required)){throw "Missing movement check: $required"}
}
$results+=@{test='native-redux-movement-all-pointers-moldyman-far-tasks-object-effects-teleport-bicycles-doors';resolvedPointers=898;teleportCycles=128;bicycleCases=16;doorBounds=6;stairCallbacks=8;exitCode=0}
Invoke-NativeCheck 'redux-screen-transitions' '--selftest-screen-transitions'
$transitionLog=Get-Content -LiteralPath (Join-Path $ScratchDirectory 'redux-screen-transitions.log') -Raw
if(!$transitionLog.Contains('21 exit/palette/brightness cases, timer step 2, PASS')){throw 'Redux fast door/warp timing did not pass.'}
$results+=@{test='redux-fast-door-warp-transition-timing';cases=21;timerStep=2;exitCode=0}
if(!$movementLog.Contains('Redux delivery letterbox: 14 timed frames, deferred music and serialized continuation, PASS')){throw 'Redux delivery sequence did not pass.'}
$results+=@{test='redux-delivery-letterbox-before-music';frames=14;exitCode=0}
Invoke-NativeCheck 'redux-audio' '--selftest-redux-audio'
$audioLog=Get-Content -LiteralPath (Join-Path $ScratchDirectory 'redux-audio.log') -Raw
if($audioLog -notmatch 'Redux SPC playback smoke: (\d+) tracks, (\d+) produced samples in (\d+) frames, PASS'){throw 'SPC playback check did not report success.'}
$results+=@{test='redux-spc-track-transitions';tracks=[int]$Matches[1];tracksProducingSamples=[int]$Matches[2];framesPerTrack=[int]$Matches[3];exitCode=0}
Invoke-NativeCheck 'redux-psi' '--selftest-redux-psi'
$psiLog=Get-Content -LiteralPath (Join-Path $ScratchDirectory 'redux-psi.log') -Raw
if($psiLog -notmatch 'Redux native PSI playback: (\d+) effects, (\d+) frames, cold-pointer rebind and extended IDs, PASS'){throw 'PSI playback check did not report success.'}
$results+=@{test='redux-psi-playback-rebind-extended-ids';effects=[int]$Matches[1];frames=[int]$Matches[2];exitCode=0}
Invoke-NativeCheck 'redux-battle-art' '--selftest-redux-battle-art'
$results+=@{test='redux-extended-enemy-battle-art';exitCode=0}
Invoke-NativeCheck 'redux-battle-sprites' '--selftest-redux-battle-sprites'
$results+=@{test='redux-party-battle-sprites-selection-victory';exitCode=0}
Invoke-NativeCheck 'redux-combat' '--selftest-redux-combat'
$results+=@{test='redux-production-combat-actions-inventory-roller';sandwichTrials=4096;gutsTrials=128;condimentRecords=42;exitCode=0}
$equipmentLog=Get-Content -LiteralPath (Join-Path $ScratchDirectory 'redux-combat.log') -Raw
if(!$equipmentLog.Contains('Redux battle Tools: 11 flag devices, maid handoff, paralysis/immobilization and inventory-free action arguments, PASS')){throw 'Redux battle Tools check did not pass.'}
$results+=@{test='redux-battle-tools-availability-inventory-free-actions';devices=11;exitCode=0}
if(!$equipmentLog.Contains('Redux menu highlight: 10 narrow/wide font cases, clear and row bounds, PASS')){throw 'Redux variable-width menu highlighting did not pass.'}
$results+=@{test='redux-font-aware-menu-highlights';fontCases=10;exitCode=0}
if($equipmentLog -notmatch 'Redux production equipment: (\d+) item/character previews.*PASS'){throw 'Equipment previews did not pass.'}
$results+=@{test='redux-equipment-preview-identity-window-remapping';previews=[int]$Matches[1];exitCode=0}
foreach($case in @(@{label='KeyItems_Title';expected='Key items'},@{label='Tools_Title';expected='Tools'},@{label='Warrior';expected='Noble Warrior'},@{label='Return';expected='Return of Flying Man'})){
 $labels=@($inventory.labels | Where-Object {$_.module -eq 'window_titles' -and $_.name -eq $case.label})
 if($labels.Count -ne 1){throw "Missing or ambiguous compiled label: $($case.label)"}
 $key='{0:X6}' -f $labels[0].snesAddress
 $address=$relocations.compiledAddresses.$key
 if(!$address){throw "Label was not converted: $($case.label)"}
 Invoke-NativeCheck ('title-'+$case.label) ('--selftest-redux-title "'+$blob+'" '+$address+' "'+$case.expected+'"')
 $results+=@{test=('native-converted-title-'+$case.label);exitCode=0}
}
$record=@{
 format='maternalbound-native-dev-validation-v1';status='development-only'
 nativeExeSha256=(Get-FileHash -LiteralPath $NativeExe -Algorithm SHA256).Hash
 packSha256=(Get-FileHash -LiteralPath $BaseAssets -Algorithm SHA256).Hash
 compiledRomSha256=$report.compiledRomSha256;convertedDialogueSha256=$report.blobSha256
 conversionCounts=$report.counts;tests=$results
 limitations=@('Isolated test sessions; this command does not replace installed game files or player saves', 'Remaining assembly-only fixes, later gameplay and full playthrough require verification', 'This command does not run the separate content-specific randomizer audit or a full randomized playthrough')
}
$record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $ScratchDirectory 'native-redux-results.json') -Encoding utf8
Write-Output 'Development checks passed; full MaternalBound parity remains unverified.'
