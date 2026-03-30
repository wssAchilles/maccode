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
- Overview remains read-only; the only compact-rail CTA is the existing soft-button that routes from overview into health details.
- Health may expose a controlled operations panel for promotion, rollback, and active-model changes, but it must read like an operator console rather than a consumer control surface.
- Operations must sit below diagnostics, separated by glass panels and explicit labels, so the health summary remains the primary information layer.
- Hover may change color and shadow only; no layout shift.
- Focus-visible must remain obvious on the CTA button.
- Any runtime degradation reason must be rendered as text, not color-only feedback.
- Primary-risk actions must require a text note field in the same panel. The note field is part of the action surface, not hidden behind a dialog in this phase.
- Buttons must keep the existing workbench button system: no icon-only controls, no floating action bars, no destructive red fills for normal rollout controls.

## Layout Rules
- Overview uses a single compact card in the right rail.
- Health uses a multi-panel diagnostic layout for runtime, rollout, comparison, model, and audit state, followed by deeper symbol-level comparison and audit timeline panels.
- The controlled operations panel belongs after diagnostics and before low-level audit overflow. It should remain two-column on desktop and collapse to one column on tablet/mobile.
- Symbol comparison rows must stay scan-friendly: symbol on the left, agreement and divergence on the right, no dense table chrome.
- The audit timeline must read newest-first and keep timestamps visually secondary.
- The component must remain within the existing workspace grid and never introduce horizontal scrolling.
- Textarea, select, and action buttons must all fit inside the glass panel without triggering horizontal scroll at `375px`.

## Content Rules
- Show only trusted fields already available from summary aggregation.
- Prefer: runtime status, configured/effective rollout mode, agreement rate, compared ticks, active model, symbol coverage, lookback, horizon, offline macro F1, blockers, latest audit event, signal distributions, symbol-level comparison, state backend, restore status, and last persisted timestamp.
- The operations panel may additionally show target mode, active registry selection, operator note, and the latest control result message.
- Omit missing metadata instead of rendering placeholder noise.
- `best_macro_f1` is an offline reference metric only; never frame it as live trading performance.
- Rollout blockers and audit messages must always be accompanied by text labels; never use color-only encoding to imply rollout readiness.
- Persistent-state details must be rendered as explicit text labels. Never imply restore success or backend health with color alone.
- Audit event titles should be normalized into operator-readable labels. Raw event payloads may appear only as short textual detail lines, never dumped as JSON in the primary surface.
- Control-result feedback must be concise and inline. Never use modal confirmations or toast spam for normal promote/rollback success paths in this phase.
