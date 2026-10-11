# October 11 song additions

The original root-site Pygame renderer is retained verbatim from the previous
`game.tar.gz` (commit 3666134). The catalog load and complete-title wrapping are
the only UI additions. `/glass/` is not rebuilt or changed by this release.

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
| Rendezvous | 1:21.5 | First refrain release; full mode now uses the replacement MP3 |
| Salt, Pepper, Birds, and the Thought Police | 1:47.8 | Include the train scene and first repeated chorus before the next section |
| String Theocracy | 0:58.6 | First refrain, before the next verse |
| Nightmare | 1:09.6 | Instrumental first-section edit, not a literal vocal verse |

The replacement `Mili - Rendezvous [Limbus Company] (1).mp3` decodes to 225.512
seconds. All three full charts were regenerated; the old 73-second duration
override was removed. Audio URLs include a content hash to avoid stale MP3 cache.
The importer detects source replacements and reanalyzes them instead of silently
reusing existing files. Salt's full title is now preserved in the display field
and wrapped in both its card and featured panel, as well as full-width screens.

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

## v3 verification

Long-title layout now chooses the largest fitting wrapped layout instead of
shrinking a six-line block. The bundled web font shows Salt's complete title in
three card lines and two featured-panel lines. Python: 98 tests passed; browser
input contract: 13 tests passed. Regression coverage includes separate durations,
decoded replacement audio, content-version URLs, complete title bounds, and all
three difficulty charts extending into full mode and clipping at each endpoint.
Catalog-count expectations were updated from 21/63 to 30 songs/90 charts.

## Analysis repair details

`auto_chart._find_onsets` could receive a four-field enriched onset when merging
another nearby pitch change, then incorrectly unpack all fields as three.
Reading its first three fields preserves the existing change score and allows
Rendezvous to finish analysis. Runtime scoring/rendering rules are unchanged.
