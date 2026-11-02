# EarthBound Companion 1.0.17 / platform preview.28

Fixes magic butterflies failing to spawn in areas without regular enemy encounters, as reported in issue #10 at Giant Step. The horizontal and vertical scroll spawn callers now preserve the original game's periodic butterfly checks even when the regular encounter ID is zero. Original and MaternalBound Redux both receive the fix. Original spawn rates, duplicate prevention and story-based spawn suppression remain in place.

The separate nearby-enemies report was checked against all 296 regular multi-enemy group compositions in each mode, using actual per-mode sprite sizes and native path movement/contact on isolated flat terrain. Those checks passed. This does not reproduce every map route or prove there is no remaining joining problem; no speculative recruitment/sprite changes were made. Joining remains limited by the original encounter group composition and reachable paths.

Validation: pre-fix native control fails; fixed Original and Redux checks pass horizontal/vertical encounter-zero scans, suppression controls, real butterfly creation, duplicate prevention/removal and the encounter fixtures. Clean pinned source accepts the full patch stack. Full campaigns and the reporter's exact route were not replayed. Existing assets and save namespaces are unchanged.

Windows is the official release. Linux, macOS and Android remain community platform previews. Android devices normally use the ARM64 APK; x64 is for emulator testing. Earlier maintenance fixes and credited game artwork are retained.
