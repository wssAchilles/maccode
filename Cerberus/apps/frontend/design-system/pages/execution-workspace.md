# Execution Workspace Override

This page inherits the global Cerberus design system and adds execution-specific rules.

## Page Intent
- The execution workspace is an operator console.
- It must prioritize decision confidence, order flow traceability, and action safety.
- Diagnostics are visible but secondary to the trade ticket.

## Layout Override
- Keep the primary ticket in the dominant column.
- Keep progress, policy, and request-trace information in a stable side rail on desktop.
- Timeline remains a separate surface and must not visually compete with the ticket header.

## Visual Override
- Use accent blue for submit/active states.
- Use teal for stable/healthy progress.
- Use red only for failure or blocked states.
- Do not rely on color alone; every progress state must also have text.

## Interaction Override
- Broker switching should feel immediate, without dramatic animation.
- Submit/cancel affordances must remain visually prominent at all breakpoints.
- Request IDs and diagnostics should be easy to scan with monospace text.

## Accessibility Override
- Progress changes must keep visible labels.
- Precheck state must remain readable without relying on the pass/fail dot alone.
- Side rail content must preserve keyboard focus order after the ticket form.
