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
 format='maternalbound-native-dev-validation-v1';status='development-only-not-playable'
 nativeExeSha256=(Get-FileHash -LiteralPath $NativeExe -Algorithm SHA256).Hash
 compiledRomSha256=$report.compiledRomSha256;convertedDialogueSha256=$report.blobSha256
 conversionCounts=$report.counts;tests=$results
 limitations=@('Isolated development pack only; installed game remains original-profile', 'Remaining title, battle effects, specialized text, music and assembly-only fixes', 'Full Redux progression and randomizer audit not run')
}
$record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $ScratchDirectory 'native-redux-results.json') -Encoding utf8
Write-Output 'Development checks passed; full MaternalBound parity remains unverified.'
