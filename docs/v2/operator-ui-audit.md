# Operator UI audit

The current frontend functions, but reads as a generic promotional dashboard rather than an engineering workstation.

- `App.tsx` opens with two blurred colour orbs, a glass nav, “Pit Wall Intelligence,” a large “Engineer the race” hero and entrance animation. The selected circuit is a decorative pill.
- The global two-column card composition mixes model configuration, Race Engineer AI and replay as equally weighted promotional surfaces rather than one task hierarchy.
- Typography relies on oversized black headings, uppercase wide tracking and large prose; numerical state gets less visual priority.
- Repeated `rounded-[2rem]`, translucent backgrounds, backdrop blur, heavy shadows, glows and hover scaling create nested-card noise.
- Controls in `Slider`, track selection and action buttons are spacious consumer controls; units and source/config status are not persistently adjacent.
- `StrategyRanking` uses individual cards and preference percentages. It lacks a comparison matrix, deltas, distributions, warnings, provenance and rejoin/traffic columns.
- `RaceEngineerPanel`, `AiModeToggle`, animated AI response/scenario cards and “unlock AI analysis” make the explainer feel like the product and can obscure deterministic evidence.
- `ReplayPanel` has a sound guided dependency flow and controlled errors, but consumes much vertical space. `ReplayAssessmentView` uses mini charts/cards where a bounded-state table and aligned alternative matrix would scan faster.
- Mobile browser tests correctly prevent horizontal overflow at 390px, but the stacked card design produces a long scroll and loses cross-option comparison.
- `App.css` contains stale `.hero` and older style-system rules alongside Tailwind composition, increasing visual inconsistency.

## Target operator interface

After backend capability exists, use a neutral dark shell, one restrained status/accent colour, compact navigation, tabular numerals, explicit timestamp/lap/track-status header, car/competitor table, aligned option matrix, sensitivity panel, and persistent warnings. State changes should be visually diffable. Every estimate should expose units, uncertainty, model version and provenance on demand. Controls should optimise keyboard use and fast scanning. Remove decorative motion, glows, hero copy, excessive rounding and AI branding; place the optional explainer after calculated evidence. On narrow screens, preserve the decision call and warnings first, then use deliberate horizontal comparison or per-option detail rather than silently destroying comparability.
