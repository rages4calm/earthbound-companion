# Bounded Jev gameplay testing

The development runner gives [TypeSafe Jev](https://docs.typesafe.ai/primitives/choice) structured native observations and a small set of ordinary button actions. The engine supplies dialogue, menus, party/battle state, NPC positions and collision data. Local code plans paths and enforces limits; Jev chooses the next permitted action. It never edits positions, inventory, story flags or decoded saves.

This is a developer tool, not a feature required to play the game. It uses the TypeSafe API and its account credentials/usage. Game observations are sent to that service when the runner is explicitly started. Keep `TYPESAFE_API_KEY` in your environment, never in source, reports or command arguments.

## Isolation and limits

- Use a copied checkpoint below `_BuildScratch`, never a player's installation.
- Every new run freezes independent engine, SDL and asset files below `_BuildScratch/jev-runs`. Existing runs cannot be overwritten.
- Each batch archives the prior saves and records inputs, native logs and observations.
- Explicit time, request and step limits stop the run. A `STOP` file also stops it between batches. Three unchanged observations stop stalled input loops.
- The observer is compiled only with `-DEB_QA_OBSERVER=ON`; normal player builds leave it off. It does not change save structures.
- A cold restore cannot reconstruct earlier dialogue prose. Carried text is labeled separately from text rendered in the current batch.

## Run a copied checkpoint

From a provisioned source workspace with `native-source` and its SDL build dependencies, configure a separate native build with `-DEB_QA_OBSERVER=ON` and audio enabled. Place its matching `SDL2.dll` beside `earthbound.exe`. Then:

```powershell
python scripts/jev_gameplay_runner.py init --directory _BuildScratch/jev-runs/my-test --native-exe build/jev-qa/earthbound.exe --assets LOCAL/Redux/assets.pak --checkpoint _BuildScratch/copied-checkpoint
python scripts/jev_gameplay_runner.py run --directory _BuildScratch/jev-runs/my-test --target-npc 155 --goal "Approach NPC 155, talk, and return to roaming" --max-steps 30 --max-requests 30 --max-seconds 60
```

The checkpoint contains `saves/quicksave_1.bin.0` and/or `.1`, plus an optional `fixture.srm` phone save. Other bounded goals are `--target X Y`, `--battle-complete` and `--heal-character 1`. For natural enemies, `--battle-complete --seek-battle` approaches observed enemy entities. `--check-before-combat` adds the reported quick Talk/Check action first. Doors can be approached using nearby waypoints; a short ordinary input probes the trigger when the conservative path planner cannot enter a solid door tile. Use `--fixture-checkpoint` for explicitly prepared scenarios so their results cannot be mistaken for normal story progression.

## Verified scope

The runner has completed an ordinary Onett walk and conversation with NPC 155, a prepared four-character combat fixture, and the player's copied Starman Junior battle through victory, level-up messages and Buzz Buzz dialogue back to roaming. The Starman test exposed a cold-restore stat-growth cache crash; that was fixed before the passing continuation. A separate replay compares player and observer builds at 46 checkpoints, checking every serialized section except raw window pointers that the engine rebuilds after loading; phone-save bytes also match.

A copied player PSI menu also passes an actual Lifeup cast: Ness heals from 51 to 63 HP, PP falls from 21 to 16, and ordinary roaming resumes after three decisions. The 46-checkpoint parity replay includes that sequence with the corrected pack. Another 20 checkpoints match through empty Talk/Check, approaching a naturally spawned Yes Man Junior, victory and roaming. That encounter takes 19 Jev decisions and does not use a prepared battle fixture. Native production rendering and structured window checks both confirm the ghost window is absent.

Jev also follows an ordinary route from the player's post-Frank checkpoint through the rear arcade door, across the arcade, out its front door and north along the Onett street. The local planner was improved to handle odd-pixel alignment, fractional movement at narrow corners and repeated-state cycles; those were QA-tool limitations, rather than additional game bugs.

There is no complete story route planner yet. This tool does not establish a completed EarthBound story, full MaternalBound Redux parity, or a completed randomized playthrough.
