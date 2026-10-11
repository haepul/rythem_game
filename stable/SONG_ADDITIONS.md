# October 11 song additions

The original root-site Pygame renderer is retained verbatim from the previous
`game.tar.gz` (commit 3666134). `main.py` only gains a data-catalog load after the
existing song list. `/glass/` is not rebuilt or changed by this release.

All nine additions have offline-generated EASY, HARD and MASTER charts. MASTER
includes ordinary flicks using the existing algorithm; existing 21 song entries
are retained. The MP3 bytes are copied from the user's Desktop/game directory.

## Short-mode boundaries

These are editorial cut points in the uploaded files, informed by lyric-section
timestamps and local PCM energy. They are estimates, not artist-provided edits
or a claimed listening-verified transcription. The existing 1.35-second fade
ends at the listed point; full mode uses the complete analyzed song duration.

| Song | Short mode end | Basis |
| --- | ---: | --- |
| 푸르름이 사는 곳 | 1:21.6 | First refrain release, before the next verse |
| 회회기담 | 1:25.9 | First refrain and following instrumental space |
| 일도 | 1:29.6 | First refrain, instrumental release |
| AIZO | 1:46.4 | Refrain after the first verse; approximate lyric timing |
| Camelia | 2:37.3 | Expanded refrain after the opening refrain and first verse |
| Rendezvous | 1:13.0 | Uploaded excerpt's existing fade; not the complete commercial song |
| Salt, Pepper, Birds, and the Thought Police | 0:54.8 | First narrative section and refrain, before the next scene |
| String Theocracy | 0:58.6 | First refrain, before the next verse |
| Nightmare | 1:09.6 | Instrumental first-section edit, not a literal vocal verse |

Rendezvous decodes to 90.07 seconds but fades to near-silence around 71–73 seconds
and remains silent afterward. Both modes end at 73 seconds for this already-short
source. A complete source file is needed for a genuinely longer full version.
The long Salt… title is retained in metadata, with `Salt, Pepper, Birds` as the
display label so it fits the existing design.

## References

- Timed lyric records (used only as section guides, not shipped lyrics):
  [푸르름](https://lrclib.net/api/get/21882306),
  [회회기담](https://lrclib.net/api/get/24646011),
  [일도](https://lrclib.net/api/get/15539153),
  [AIZO](https://lrclib.net/api/get/34285090),
  [Camelia](https://lrclib.net/api/get/15594862),
  [Rendezvous](https://lrclib.net/api/get/38950184),
  [Salt…](https://lrclib.net/api/get/33403807),
  [String Theocracy](https://lrclib.net/api/get/32340054).
- BPM interpretation hints, followed by analysis of local audio:
  [Nightmare](https://wikiwiki.jp/cytus-2/Nightmare),
  [Camelia](https://bpm-database.tokyo/music/7VT08Ro1),
  [Salt…](https://www.hooktheory.com/theorytab/view/mili/salt-pepper-birds-and-the-thought-police),
  [AIZO](https://songbpm.com/%40king-gnu/aizo-f0x0y).

## Analysis repair

`auto_chart._find_onsets` could receive a four-field enriched onset when merging
another nearby pitch change, then incorrectly unpack all fields as three.
Reading its first three fields preserves the existing change score and allows
Rendezvous to finish analysis. Runtime scoring/rendering rules are unchanged.
