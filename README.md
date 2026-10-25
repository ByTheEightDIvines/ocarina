# Ocarina Horse Call (Dusklight mod)

Replaces the Horse Call with a low-poly blue ocarina, and calling Epona (with the charm or a
horse-grass reed) plays a custom ocarina tune with a canyon echo on the last note.

- `overlay/` – ocarina models (hand, Ilia charm, cutscene pendant) and the tune stream
  `Audiores/Stream/horse_ocarina.ast` (a new file, nothing on disc is overwritten).
- `textures/` – HD ocarina texture.
- `src/mod.cpp` – registers the tune as a new stream and hooks `Z2CreatureLink::startLinkVoice`
  so `Z2SE_PLAY_REED_UMAKUSA` (0x20023) plays the tune instead of the reed melody.
  `Z2Sound.baa` is never modified, so it works alongside other sound mods.
- `audio-source/` – the original recording, the echo/mastering script and the AST encoder.

GitHub Actions builds every platform; download the `mod-combined` artifact for the all-platform `.dusk`.
