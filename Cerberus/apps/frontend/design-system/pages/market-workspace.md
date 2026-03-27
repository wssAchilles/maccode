# Market Workspace Override

This page inherits the global Cerberus design system and adds market-monitoring rules.

## Page Intent
- The market workspace is a live monitoring surface.
- It prioritizes quote awareness, signal visibility, and order book readability.
- Chart and order book must feel synchronized, but they should not compete for emphasis.

## Layout Override
- Keep symbol switching inside the section header so context changes remain local.
- Reserve the wide column for charting and diagnostics.
- Keep the order book in a stable side rail on desktop and collapse it below the chart on narrow viewports.

## Visual Override
- Preserve the existing light glass tokens from the global master.
- Use teal for buy-side and blue/neutral accent for active market context.
- Empty or stale market states must remain legible without dim gray-on-glass treatment.

## Interaction Override
- Symbol toggles must feel immediate and expose hover, active, and focus-visible states.
- Market metric tiles may animate content opacity, but must not shift layout on refresh.
- Chart and order-book refresh cues should be subtle and respect `prefers-reduced-motion`.

## Accessibility Override
- The order book stale state must include text, not color alone.
- Chart containers must preserve a clear label and stable keyboard flow around adjacent controls.
- Diagnostics content must remain copyable and readable with monospace formatting.
