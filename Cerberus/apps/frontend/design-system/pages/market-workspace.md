# Market Workspace Override

This page inherits the global Cerberus design system and adds market-monitoring rules.

## Page Intent
- The market workspace is a live monitoring surface.
- It prioritizes quote awareness, signal visibility, and order book readability.
- Chart and order book must feel synchronized, but they should not compete for emphasis.

## Layout Override
- Keep symbol switching inside the section header so context changes remain local.
- Reserve the wide column for charting and diagnostics.
- Keep the strategy basket under the chart so the operator can read market context before deeper diagnostics.
- Keep the portfolio summary and order book in a stable side rail on desktop and collapse them below the chart on narrow viewports.
- The portfolio summary may expose tracked symbol chips; those chips should let the operator pivot the whole market context without opening another workspace.

## Visual Override
- Preserve the existing light glass tokens from the global master.
- Use teal for buy-side and blue/neutral accent for active market context.
- Empty or stale market states must remain legible without dim gray-on-glass treatment.
- Order book summary cards should stay compact and numeric, not become decorative market tiles.

## Interaction Override
- Symbol toggles must feel immediate and expose hover, active, and focus-visible states.
- Market metric tiles may animate content opacity, but must not shift layout on refresh.
- Chart and order-book refresh cues should be subtle and respect `prefers-reduced-motion`.
- Strategy cards must behave like read-only diagnostic surfaces, not pseudo-buttons.

## Accessibility Override
- The order book stale state must include text, not color alone.
- Chart containers must preserve a clear label and stable keyboard flow around adjacent controls.
- Diagnostics content must remain copyable and readable with monospace formatting.
