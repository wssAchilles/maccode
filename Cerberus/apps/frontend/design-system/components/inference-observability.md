# Inference Observability

## Purpose
- Surface model/runtime visibility inside the authenticated workbench.
- Keep the module read-only in this phase.
- Support both `Overview` and `Health` without creating a new workspace.

## Visual Rules
- Use existing light glass panels with visible border and high-contrast text.
- Keep the panel information-dense but quiet: status pill, short summary line, compact data list.
- Do not use emoji or decorative illustrations.
- Do not add bespoke colors inside the component. Reuse global status, border, and text tokens.

## Interaction Rules
- The only interactive affordance is the existing soft-button that routes from overview into health details.
- Hover may change color and shadow only; no layout shift.
- Focus-visible must remain obvious on the CTA button.
- Any runtime degradation reason must be rendered as text, not color-only feedback.

## Layout Rules
- Overview uses a single compact card in the right rail.
- Health uses a two-panel diagnostic layout that collapses to one column on tablet/mobile.
- The component must remain within the existing workspace grid and never introduce horizontal scrolling.

## Content Rules
- Show only trusted fields already available from summary aggregation.
- Prefer: runtime status, mode, engine, active model, symbol coverage, lookback, horizon, offline macro F1, reason.
- Omit missing metadata instead of rendering placeholder noise.
- `best_macro_f1` is an offline reference metric only; never frame it as live trading performance.
