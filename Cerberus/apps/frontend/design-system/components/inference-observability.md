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
- Health uses a multi-panel diagnostic layout for runtime, rollout, comparison, model, and audit state, followed by deeper symbol-level comparison and audit timeline panels.
- Symbol comparison rows must stay scan-friendly: symbol on the left, agreement and divergence on the right, no dense table chrome.
- The audit timeline must read newest-first and keep timestamps visually secondary.
- The component must remain within the existing workspace grid and never introduce horizontal scrolling.

## Content Rules
- Show only trusted fields already available from summary aggregation.
- Prefer: runtime status, configured/effective rollout mode, agreement rate, compared ticks, active model, symbol coverage, lookback, horizon, offline macro F1, blockers, latest audit event, signal distributions, symbol-level comparison, state backend, restore status, and last persisted timestamp.
- Omit missing metadata instead of rendering placeholder noise.
- `best_macro_f1` is an offline reference metric only; never frame it as live trading performance.
- Rollout blockers and audit messages must always be accompanied by text labels; never use color-only encoding to imply rollout readiness.
- Persistent-state details must be rendered as explicit text labels. Never imply restore success or backend health with color alone.
- Audit event titles should be normalized into operator-readable labels. Raw event payloads may appear only as short textual detail lines, never dumped as JSON in the primary surface.
