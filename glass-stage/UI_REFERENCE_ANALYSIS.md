# Rhythm Stage UI reference analysis — 2026-10-13

All four supplied pages and their actual screenshot images were inspected before changing code. Measurements below are approximate proportions from displayed screenshots, not extracted original design specifications. No reference image is included in the game.

| Reference | Observed structure | Independent 800 × 480 adaptation |
|---|---|---|
| [Official gameplay](https://colorfulstage.com/aboutgame/gameplay/) | Actual difficulty legend: green EASY, orange HARD, purple MASTER; bold white lettering; soft navy backdrop and dots. | Preserve the game's three existing difficulties, with these distinct color families. |
| [Song selection redesign](https://yashihei.hatenablog.com/entry/2023/12/30/181813) | Square jackets in a three-column grid; selected jacket has a thicker light frame; right detail panel occupies about 40% of width; pastel lavender background; active difficulty is filled. | Grid x24–470, detail x492–776; six square jackets per page; all 30 songs remain accessible. White cards, cyan selection frame, violet detail header. No unsupported search, categories, rewards or currency. |
| [Result screen](https://note.com/5gkyu/n/n1edbb0c9617f) | Song strip at top (~13% height), large score in left middle, separate judgments and combo block below, rank and character area on right, primary/secondary actions at bottom. | Top song strip, large pink score, separate three-judgment statistics, original geometric rank medallion instead of character art. Actual accuracy/combo/practice state only. |
| [Pause screen](https://notes.qoo-app.com/en/note/1740668) | White modal approximately x23–77%, y29–71%; cyan header ~23% of modal height; three rounded buttons, cyan resume, subtle lower shadows; dark visible stage behind. | Taller central white modal to retain this game's volume, speed and flick controls. Stable dimmed stage snapshot, cyan resume and restrained secondary buttons. |

Actual images viewed: blog `20231230155754.png`; official `play_img02_ver02.jpg`; result `picture_pc_98ebf8b9c0a598f222a7b39b28079948.png`; Qoo `76d87744e2a689ecc14b0f08f138613a.jpg`. Qoo's text fetch failed, but its screenshot loaded and was visually inspected in the browser.

Typography: bold sans-serif, 12–14 px metadata, 16–20 px controls/titles, 30–48 px score/rank. Screenshot tracking cannot be measured reliably; avoid artificial spacing in Korean. Use licensed Nanum Gothic Bold for identical desktop/web metrics, with its OFL notice. Main panels radius 10–16 px, controls 6–10 px, 1 px highlight and 2–3 px restrained shadow. Cyan #19D4C5, mint #66E9D2, white #F8FAFF, dark ink #41445C, pink #FF69B5, violet #343454.

Static screenshots do not establish animation durations. Our own transitions use 180 ms menu fades and 140 ms selection accents; no delay is added to music, judgments or input. Gameplay remains dark with the existing perspective, notes and track. Decorative art is procedural geometry; no logo, character, UI sprite or original jacket was copied.
