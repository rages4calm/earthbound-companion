# EarthBound Companion 1.0.19 / platform preview.30

Fixes the party walking toward or riding the wrong bus when a scheduled passenger bus and a passing traffic bus are loaded together, as reported in issue #11 after Threed/Threek. Both vehicles share sprite205. The original lowest-slot sprite lookup could send boarding-position, departure-movement and camera commands to the unrelated traffic bus. Bus lookups now prefer the active dialogue-created passenger vehicle, with the existing first active traffic match as fallback when no passenger bus exists. Other sprite lookup rules are retained.

The correction applies to Original and MaternalBound Redux. Existing assets and saves remain compatible; ROM conversion is not required again.

Focused verification: old code selects the wrong bus; fixed code passes 150 configurations in each mode, covering 25 passenger route/arrival script IDs, both slot orders, the real boarding-position callroutine and actual post-fare movement/camera bytecode. The traffic bus stays unchanged. Inactive bus and ordinary sprite controls pass. The complete 18-patch chain applies to clean pinned source. These isolated fixtures do not establish a full replay of the reporter's bus journey or a full campaign.

Windows is the official release. Linux, macOS and Android remain community previews. Android devices normally use the ARM64 APK; x64 is for emulator testing. Earlier maintenance fixes and credited artwork are retained.
