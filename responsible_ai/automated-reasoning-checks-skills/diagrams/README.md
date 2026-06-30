# Diagrams

Visual set for the Automated Reasoning Checks skill suite. **SVG is the master** (editable vector);
PNGs are rendered exports (`@3x` for blog/print).

| File | Shows |
|---|---|
| `01-translate-validate` | How one check works: language models translate words → logic; an SMT solver validates. Where bugs come from. |
| `02-lifecycle` | The six Agent Skills across build-time (1–4) and runtime (5–6), with the fix-and-re-test and Valid@N loops. |
| `03-rewrite-loop` | The runtime rewrite loop: answer → check → verdict → rewrite with the broken rule → repeat until VALID. |
| `04-architecture` | What's inside the suite: six skills over a shared library + reference docs. |

## Visual system

- **Palette:** squid-ink navy `#232F3E` (runtime/structure), Smile-orange `#FF9900`/`#EC7211` (flow & loops),
  cool paper `#FBFBFA`, hairline `#E3E7EB`. Verdict colors: green `#1D8102`, red `#D13212`,
  amber `#B7791F`, deep-red `#9B1C0B`, violet `#6B46C1`.
- **Type:** Avenir Next (display/body), Menlo (the SMT-LIB code accents).
- **Convention:** orange-topped cards = build-time skills; navy cards = runtime; orange arrows = loops.

## Sizing

All four share a **standard canvas of 1200×556** (SVG). Exports: `.png` = 2× (2400×1112),
`@3x.png` = 3× (3600×1668) for blog/print.

## Re-render PNGs

Edit the `.svg`, then (headless Chrome):

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
for n in 01-translate-validate 02-lifecycle 03-rewrite-loop 04-architecture; do
  "$CHROME" --headless --disable-gpu --force-device-scale-factor=3 --hide-scrollbars \
    --default-background-color=ffffffff --window-size=1200,556 \
    --screenshot="$n@3x.png" "$n.svg"
done
```
