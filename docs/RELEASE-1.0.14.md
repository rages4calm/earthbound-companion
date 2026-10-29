# EarthBound Companion 1.0.14 / platform preview.25

Setup failures now offer **Save error report**. The text file includes platform and runtime versions, setup progress, the exception and current helper logs. PyInstaller's generic last-line crash banner no longer hides the useful exception above it. Local home, installation and selected ROM paths are redacted; no ROM, asset pack or save is included. An unwritable log directory does not prevent exporting the Windows report from memory.

On Android, Start and Select sit at the upper-left; Save, Load, Fast and Settings sit at the upper-right, leaving the center clear. These utility buttons have smaller visual backgrounds and labels while retaining touch targets at least 48 dp tall. Movement and face/shoulder controls are unchanged. **Controls → Show touch controls** still hides the overlay for controller users.

This update adds diagnostics; it does not establish or fix the cause of the reported `ebtools_setup_entry` crash. Native gameplay binaries and the pinned Redux source are unchanged. Existing saves and game data remain compatible.
