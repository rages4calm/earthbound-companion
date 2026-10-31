# EarthBound Companion 1.0.15 / platform preview.26

Fixes a movement lock when a normal save loads the party inside a respawned NPC, as reported near Frank. Steps reducing an existing overlap with a normal NPC are now allowed. Stationary overlap, movement deeper into an NPC, entering one from outside, and enemy collisions retain their existing behavior.

Existing saves need no editing or conversion. This is a native movement correction for both game editions; pinned Redux data, randomizer recipes and save namespaces are unchanged.

Earlier focused native checks and the reporter's confirmation are retained. This release rebuilds the packages without additional gameplay or runtime tests, at the owner's request. Setup report export and Android touch layout improvements remain included.
