# Health Workspace Override

This page inherits the global Cerberus design system and adds diagnostics-specific rules.

## Page Intent
- The health workspace is an observability panel for operators.
- It prioritizes state clarity, persistence visibility, and traceability over decorative presentation.
- Diagnostics must stay interpretable under degraded conditions.

## Layout Override
- Keep high-level service health in the dominant row.
- Use paired glass panels for worker/store breakdown so values scan vertically.
- Keep request IDs and diagnostic payloads in a side rail that never displaces primary status cards.

## Visual Override
- Preserve the global light glass system.
- Use accent blue for active loading, teal for healthy states, amber/red only for warning or failure.
- Request and diagnostic payloads should use monospace styling and stronger border contrast than standard body content.

## Interaction Override
- Expanding diagnostics should not reflow the surrounding layout abruptly.
- Error surfaces must expose clear summary copy before raw JSON.
- Dense data lists should remain tappable and readable on tablet widths.

## Accessibility Override
- Health state must always include visible text labels.
- Diagnostic drawers must keep keyboard focus order predictable.
- Degraded and error states must surface reason text alongside status color.
