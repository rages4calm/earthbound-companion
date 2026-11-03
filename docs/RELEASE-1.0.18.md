# EarthBound Companion 1.0.18 / platform preview.29

Fixes cinematic bars staying on screen after answering No to Carpainter without the Franklin Badge and being teleported outside. The pinned Redux No branch omitted the timed closing sequence already present in Yes. Both now use the existing 145-frame wait and animated close. The narrow native adapter checks the relocated labels and exact existing cleanup suffix; it does not change converted asset bytes, pack identity or save cursors. Existing asset packs remain usable.

Focused verification: old native control fails; No and Yes cleanup continuations pass with cinematic bars visible and hidden, including scalar continuation round-trip, unrelated-offset and modified-suffix controls. Original mode leaves the adapter inactive. The previous delivery-letterbox regression passes, and the full 17-patch stack applies to clean pinned source. The complete lightning/teleport scene and full campaigns were not replayed. The badge/battle route is outside this adapter's matched endpoint.

Windows is the official release. Linux, macOS and Android remain community platform previews. Android handhelds, phones and tablets normally use the ARM64 APK; x64 is for emulator testing. Previous maintenance fixes and credited artwork are retained. Owner installations and saves were not modified.
