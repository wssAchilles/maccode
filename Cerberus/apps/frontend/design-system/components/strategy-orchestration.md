# Strategy Orchestration Component

This component family covers the read-only strategy basket, portfolio signal summary, and execution lifecycle panels inside the authenticated workbench.

## Intent
- Show how the effective signal is formed from multiple strategies without exposing raw debugging noise.
- Keep orchestration detail close to market and execution context, not as a detached admin screen.
- Emphasize operator comprehension over decorative flourish.
- Surface whether the current basket is executable, contested, or still in a hold posture.
- Keep tracked symbols interactive so operators can pivot the whole workbench without opening a second control surface.

## Visual Rules
- Use the existing light glass tokens from `MASTER.md`; do not introduce darker subthemes.
- Treat `BUY` as teal-positive, `SELL` as red-negative, and `HOLD` as accent-neutral.
- Signal emphasis must always include text, not color alone.
- Use compact data rows and operator-style labels rather than large marketing cards.

## Layout Rules
- `StrategyDecisionMatrix` is a dense vertical list of strategy cards with stable spacing.
- `StrategyPortfolioPanel` is concise and should sit in the side rail on desktop.
- `StrategyPortfolioPanel` may expose tracked symbol chips, but those chips must reuse the global chip treatment and never look like a primary CTA.
- `ExecutionLifecyclePanel` belongs above the trade ticket so operators see constraints before action.
- `ExecutionLifecyclePanel` includes a four-step stage rail before the detail list: dispatch, policy, venue rule, execution feedback.
- On narrow viewports, metadata grids collapse to one column before introducing overflow.

## Interaction Rules
- These panels are read-only and should not imply hidden controls.
- Hover states may deepen border/shadow only; no motion that shifts layout.
- Any status changes should be handled through standard pills and inline text.
- Symbol chips may change the active workbench symbol, but they must remain compact and avoid modal behavior.

## Accessibility Rules
- Every status needs a label and readable contrast against the glass surface.
- Empty states must explain what data is missing and why.
- Dense metadata remains keyboard-readable and should not rely on tooltips for core meaning.
- Execution stage rail must be understandable through text labels alone; color only reinforces state.
