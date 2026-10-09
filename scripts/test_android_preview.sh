#!/usr/bin/env bash
set -euo pipefail
adb install -r build/apk/EarthBound-Companion-android-x64-preview.apk
adb logcat -c
adb shell am start -n org.earthbound.companion.preview/org.earthbound.companion.ManagedLauncher --ez portableSmokeTest true
for attempt in $(seq 1 30); do
  adb logcat -d > build/android-smoke.log
  if grep -q 'Companion ROM-free native selftest: PASS' build/android-smoke.log && grep -q 'Managed settings and recipe JSON round-trip: PASS' build/android-smoke.log; then
    adb shell pidof org.earthbound.companion.preview
    echo 'Managed Android launcher and SDL native input/MSU selftest passed; no gameplay claimed.'
    exit 0
  fi
  if grep -qE 'FATAL EXCEPTION|Fatal signal|Companion ROM-free native selftest: FAIL' build/android-smoke.log; then
    tail -n 150 build/android-smoke.log
    exit 1
  fi
  sleep 2
done
tail -n 150 build/android-smoke.log
exit 1
