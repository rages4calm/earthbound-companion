#!/usr/bin/env bash
set -euo pipefail
adb install -r build/apk/EarthBound-Companion-android-x64-preview.apk
adb logcat -c
dump_failure() {
  adb logcat -b crash -d
  grep -E 'org\.earthbound|AndroidRuntime|CompanionSmoke|monodroid|mono-rt|DOTNET|SDL|Fatal signal' build/android-smoke.log | tail -n 150 || true
}
adb shell am start -n org.earthbound.companion.preview/org.earthbound.companion.ManagedLauncher --ez portableSmokeTest true
for attempt in $(seq 1 30); do
  adb logcat -d > build/android-smoke.log
  if grep -q 'Companion ROM-free native selftest: PASS' build/android-smoke.log && grep -q 'Managed settings and recipe JSON round-trip: PASS' build/android-smoke.log; then
    adb shell pidof org.earthbound.companion.preview
    sleep 2
    adb shell settings put system accelerometer_rotation 0
    adb shell settings put system user_rotation 1
    sleep 2
    adb logcat -d > build/android-smoke.log
    test "$(grep -c 'Managed smoke activity created' build/android-smoke.log)" = 1
    grep -q 'Managed launcher configuration changed without activity recreation' build/android-smoke.log
    adb shell settings put system user_rotation 0
    sleep 2
    adb shell screencap -p /sdcard/companion-preview.png
    adb pull /sdcard/companion-preview.png build/android-launcher-smoke.png
    echo 'Managed Android launcher and SDL native input/MSU selftest passed; no gameplay claimed.'
    exit 0
  fi
  if grep -qE 'FATAL EXCEPTION|Fatal signal|Companion ROM-free native selftest: FAIL' build/android-smoke.log; then
    dump_failure
    exit 1
  fi
  sleep 2
done
dump_failure
exit 1
