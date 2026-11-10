# DAY 12 — free stickers, bonus progress, exchange, inventory

Requested task date: **2026-11-06**. Actual local verification: **2026-11-07 KST**.
Checkout: `C:\Users\MSII\Documents\Codex\rythem_game-pages-staging`.
Branch: `main`; origin: `https://github.com/haepul/rythem_game.git`.
HEAD remains `77451317d7d3f7a68a36f54d8de0c932769465cb`.
No commit, push, or deployment was performed.

## Preflight and protected work

Ran Git root/origin/branch/HEAD/status, `git log -3 --oneline`, `git worktree list`, and `rg --files next-stage tests`; checked applicable ancestor/checkout AGENTS files (none found). There was one worktree. DAY 8–10 changes were already uncommitted and were preserved. DAY 11 inventory was absent and was implemented/tested first; see `day11.md`.

No changes to core judgment, score, LIFE, audio, charts, renderer, note skin, menu-navigation, base style/ui-system, original site, or glass-stage. `app.mjs` only changes the gacha import version; `index.html` only changes gacha CSS/app cache versions. Existing song `[data-view]` navigation is unchanged.

## Project-only rules

`reward-config.mjs` is the shared, deeply frozen registry. `free-rewards-v1` is a project free simulation rule, not Project SEKAI's policy:

- Eligible banners: demo-mint, demo-lilac, demo-peach, each with separate stickers/progress.
- Each committed draw card: 1 sticker + 1 progress point.
- Every 10 progress: 2 extra stickers, retaining the remainder.
- Exchange: 10 stickers of that banner for one configured placeholder card (test-card-001…006, R2/R3/R4).
- Exchange grants no progress or bonus. No expiration, cash value, ticket, payment, or merchandise.
- First policy applies retroactively to old valid draws. The banner UI explains this explicitly.
- Existing crystal grant remains once per browser data, 3,000; draw cost 300/3,000, rates 80/15/5, and no guarantee are unchanged. One legitimate free 10-draw yields 12 stickers, enough for one exchange; repeated QA uses isolated fixtures.

Do not edit a published rule registry entry. Add a new version for later policy changes. Each draw transaction pins its reward version; exchange requests pin rule version/card/cost. `LEGACY_REWARD_VERSION` is independently fixed to the first policy so later defaults cannot reinterpret old v1/v2 data. Progress is keyed by banner and rule version; sticker totals retain the amounts calculated under historical rules.

## Storage and migration

Key remains **`rhythm-next-gacha-wallet-v1`**; payload is schemaVersion **3**:

```js
{
  schemaVersion: 3,
  balance, claimedGrantIds,
  receipts: [/* original committed draw receipts, unchanged */],
  exchanges: [{request: {requestId, bannerId, ruleVersion, cardId, rarity, cost},
               stickersBefore, stickersAfter, committedAt}],
  transactions: [
    {kind: 'draw', id: 'draw-request-id', rewardVersion: 'free-rewards-v1'},
    {kind: 'exchange', id: 'exchange-request-id'}
  ]
}
```

`transactions` is the authoritative acquisition order, never timestamp sorting. It contains only references and policy metadata, not duplicated cards or inventory counts. Each source has exactly one matching reference, source arrays retain their order, IDs are globally unique across draw/exchange, and historical sticker before/after values must match ledger replay. Cards remain in their original draw receipt or explicit exchange record. Sticker balances, progress, inventory, and NEW are read-only projections.

Migration example: v2 balance 0, claimed grant, one 10-card receipt → v3 preserves balance/claims/receipt byte values and order; adds one first-policy draw reference, no exchange. Derived stickers = 12, progress = 0. Exchanging card006 → credits still 0, one exchange/reference appended, stickers = 2, total cards = 11. v1 preserves balance/claims and starts with empty history. Repeated migration/read does not grant additional stickers or credits.

Reading migrates in memory only. The next successful locked write saves the migrated snapshot together with the operation. If that write fails, original v1/v2 bytes remain unchanged. Explicit `store.migrate()` is also idempotent. Corrupt data, unknown rule versions, and future schema are rejected without reset. Existing confirmed recovery affects only this gacha key.

## Atomic service and result contracts

The same origin/key Web Lock protects grants, draws, migration, exchange, and recovery:

1. Read latest saved state and validate/migrate inside lock.
2. Check global request ID and full request identity.
3. Recalculate current same-banner stickers and validate pinned policy/card/cost.
4. Append cost+card exchange and ordered reference to one snapshot.
5. Perform one `setItem`; only then return success and update UI.

Identical request retries return the prior exchange without writing or spending; altered contents or cross-kind IDs are rejected. Service busy guards supplement UI locks. Failed writes retain the same pending intent; **저장 상태 다시 확인** refreshes storage and permits retry with that request ID. A storage error does not trap the user in the dialog: closing preserves unresolved intent while allowing the existing recovery UI to be reached. Closing while committing is disabled. Screen exit cannot undo a committed exchange.

The existing store handles quota/read/write errors, readback of a write that threw after acceptance, and broken UI subscribers. Web Locks unavailable → read-only limitation, not an unsafe localStorage transaction fallback. Older v1/v2 clients reject schema 3; writers must continue using the same key/lock. Manual storage tampering or noncooperating scripts are outside localStorage integrity guarantees. No history pruning; quota failure is reported rather than silently dropping receipts.

`acquisitions(wallet)` returns ordered source entries for inventory and NEW. `buildResultModel(receipt,{wallet})` scans acquisitions before that draw, including exchanges. Draw A → exchange card X → draw B containing X means B is not NEW; A's old NEW flags remain unchanged, even at identical timestamps. Missing/invalid history remains unknown. Result display does not call debit, RNG, or writes.

## UI and lifecycle

Banner rules/stickers/numeric progress/next bonus/exchange button share the registry. Exchange offers configured cards, rarity text, cost, projected balance or exact missing amount, confirmation/cancel, saved success, inventory, and original-banner return. Store notifications update current confirmation balance and disabled state without replacing the chosen card or focus. Inventory filters and sorts never write.

Native shared modal handles focus, Escape, and background blocking. New controls are at least 44px, wrap long IDs, and use scoped gacha CSS/tokens. Mobile lists use one column. No new animation, blur, Pixi app, RAF, or particles; existing effects OFF/reduced-motion handling remains. Projection work occurs on state/UI changes, not the game frame loop. History processing/storage is O(history) in projections, with full snapshot validation; large-history performance is not benchmarked.

## Changed files

- New: `gacha/reward-config.mjs`, `acquisition-history.mjs`, `exchange-service.mjs`, `exchange-view.mjs`, `inventory-model.mjs`, `inventory-view.mjs`.
- Extended: `wallet-config.mjs`, `wallet.mjs`, `wallet-storage.mjs`, `draw-service.mjs`, `result-model.mjs`, `draw-view.mjs`, `view.mjs`, `details.mjs`, `gacha.css`.
- Cache alignment only where otherwise unchanged: gacha import chains, `app.mjs`, `index.html`, associated test imports/HTML fixtures (`20261106-day12`).
- Tests: `test_gacha_inventory.mjs`, `test_gacha_exchange.mjs`; schema expectation in `test_gacha_flow.mjs`.
- Fixtures: `gacha-exchange.html`, `gacha-responsive.html`; `gacha-flow.html` now appends a matching transaction for its synthetic later receipt; `gacha-play.html?isolation=day12` uses a separate test prefix.
- Documentation: this file, `day11.md`, `day12-test-results.txt`, `day12-captures/`.

## Automated verification

From checkout root, PowerShell:

```powershell
$t = (Get-ChildItem tests/test_gacha*.mjs).FullName
node --test @t tests/test_menu_navigation.mjs
# 220 tests, 220 passed, 0 failed/skipped
node --check next-stage/app.mjs
# Also node --check on every next-stage/gacha/*.mjs
node tests/test_judgment_3d.mjs
# PASS: geometry, layers, OFF, reflection, hot path, pools and engine scores
git diff --check
# Exit 0; only an LF/CRLF normalization warning
```

Exchange coverage includes 9→10, 9→19, banner separation, immutable rules, v1/v2 repeated migration, exact cost/one short, cancellation, rapid20confirm, same/different ID retry, two-tab serialized races, cross-kind IDs, quota error, migration+exchange failed write preserving original bytes, forged ledger/cost rejection, broken UI subscriber after commit, refresh restore, read-only inventory sorting/filtering, draw→exchange→draw NEW, unsupported locking/corrupt/future data, and no extra RNG/crystal debit. Full output: `day12-test-results.txt`.

## Actual browser evidence

Used the in-app Chromium browser at localhost:8785. Only isolated fixture keys were written, never the user's normal records:

- `rhythm-next-day12-exchange-fixture`: actual grant→10-draw→exchange. 3 total writes (grant/draw/exchange), 20 RNG samples for the draw, credits 0, stickers 2, total cards 11. Reload: 0 new writes/0 RNG and same transaction/quantity data.
- Empty inventory, R3 filter with no matches, R4 acquisition disclosure, rarity sort, and corrupt-data error differentiated.
- Simulated one-shot quota error: credits 3000/stickers12/cards10 retained, then same-request retry saved once, stickers2/cards11; no draw RNG.
- Two actual tabs: A confirming card005 at12; B exchanged card006; A retained selected card/focus and changed to2/“8장 더 필요”, disabled confirm. No second debit.
- `gacha-play.html?isolation=day12&fixture=short`: production app/module flow, actual grant and 10-draw, Escape skip to saved results, exchange006, inventory11, return to Cry Baby MASTER unchanged. General play entered, paused/resumed, short fixture result saved (1 MISS, score0); practice entered and paused. Reload restored exchange banner message and inventory. No error/warn logs in this app tab.
- 360×800 and 844×390: real-size iframe content/media queries; one-column mobile inventory, no modal horizontal overflow, close button remained inside the content viewport. 1366×768 and CSS200%: modal contained, scrollable content, keyboard Enter/Space/Escape worked. At200%, measured modal right1327/bottom744, close bottom711 within1366×768. This was **CSS zoom**, not OS/browser zoom.

The browser viewport override did not apply (DOM still reported desktop dimensions), so `gacha-responsive.html` provided actual-sized iframe viewports. Initial screenshots failed; later capture recovered. Inspected saved desktop/confirmation/mobile/landscape captures. No claim of physical mobile touch, Safari/Firefox, screen-reader, OS reduced-motion setting, actual browser200% zoom, audio listening/sync measurement, FPS, or long-session storage stress testing.

Captures: `day12-captures/app-inventory.png`, `exchange-confirm.png`, `inventory-360-full.png`, `inventory-landscape.png`. Their fixture data may differ because explicit test-seed controls were used; none is an operating-record reset. `browser-evidence.json` records geometry and counters.

## Status / remaining limits

Local DAY11 prerequisite + DAY12 implementation and automated/browser functional verification are complete. No known failing test remains. No commit/push/deployment. Rules and snapshots remain local-browser free simulation data, not a trusted server economy. Full history is retained, so eventually localStorage quota can prevent further writes; explicit error/retry is the supported behavior. Device, accessibility-assistive-tech, audio, performance and browser-zoom checks listed above remain unexecuted.
