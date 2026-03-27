# Overview Workspace Override

This page inherits the global Cerberus design system and adds command-center rules.

## Page Intent
- The overview workspace is the operator command center.
- It must summarize market, strategy, execution, and health without feeling like a marketing hero page.
- Quick actions are secondary to system comprehension.

## Layout Override
- Keep the hero section operational: metrics first, actions second.
- Core flow remains the dominant central surface.
- Health digest, recent signals, and persistence blocks should read as a stacked briefing rail.

## Visual Override
- Preserve the global light glass palette and typography.
- Use accent blue for navigational CTA emphasis and teal for healthy system feedback.
- Summary warnings should be visible but should not visually overpower the hero metrics.

## Interaction Override
- Workspace shortcuts must look obviously clickable and keep stable hover states.
- Metric tiles should emphasize scan speed over decorative motion.
- Secondary drill-down actions should remain grouped and predictable across breakpoints.

## Accessibility Override
- Summary alerts must remain readable with `role="alert"` semantics from the shared component layer.
- CTA groups must maintain visible focus order and spacing on mobile.
- Recent signal cards must preserve readable time and confidence values without relying on color alone.
