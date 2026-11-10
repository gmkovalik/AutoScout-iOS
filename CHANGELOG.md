# AutoScout Mobile change log

## First full mobile port
- Reuses AutoScout 4.1.0 non-GUI Python engine.
- Applies the original maroon/white/slate visual identity and logo.
- Adds touch-first navigation and mobile cards.
- Includes event loading, session saving, team overrides, match predictions, standings, alliance report, analysis, scouting notes, team research, scout roster, watchlist and assignments.
- Adds Windows Python 3.11 preview scripts and GitHub Actions macOS Xcode-project generation.

## Mobile UI color and selection update
- Added red- and blue-alliance color coding to match cards and match details.
- Actual completed-match winners are emphasized using the winning alliance color; upcoming matches retain predicted win probabilities.
- The selected team (defaulting to the configured team number) is highlighted across team lists, match alliance rows, standings, and alliance reports.
- Selecting a team from the team list/standings updates and saves the highlighted team.
- Fixed standings rendering to use the real `Standing` fields (`wins`, `losses`, `rp`) and retrieve CAP from the corresponding team stats, rather than referencing nonexistent `ties`/`cap` fields.


## v4 — visual and layout repair
- Rebuilt match list rows as compact cards with responsive text sizing; removed the overlapping fixed-height detail strip that caused clipped text.
- Made match headings explicitly distinguish final scores from predicted winners.
- Red and Blue alliance rows now use stronger winner colors, with a separate selected-team highlight.
- Replaced the fake single-value chart bars with grouped CAP / OPR / EPA horizontal bar charts, a plotted alliance win-rate curve, and a color-coded match win-probability view.
- Made chart rows open the selected team's detail page.
- Replaced the unsupported hamburger glyph with a readable MENU button.
