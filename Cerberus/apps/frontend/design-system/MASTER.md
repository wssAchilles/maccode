# Cerberus Frontend Design System

This file is the global source of truth for all UI work in `apps/frontend`.

## Mandatory Workflow
- Every new page, redesign, or major UI extension must start with `ui-ux-pro-max`.
- Recommended query baseline:
  - `python3 /Users/achilles/.codex/skills/ui-ux-pro-max/scripts/search.py "fintech real-time trading dashboard glass light professional" --design-system -f markdown -p "Cerberus"`
- Supplement with:
  - UX: `--domain ux "dashboard accessibility interaction motion"`
  - React: `--stack react "state hooks performance architecture"`

## Product Direction
- Product type: real-time fintech trading dashboard
- Design pattern: high-density operator workspace, not a marketing landing page
- Style: light glassmorphism with strong contrast
- Mood: precise, calm, premium, trustworthy
- Information density: high, but always scannable

## Visual Tokens
- Primary: `#0F766E`
- Secondary: `#14B8A6`
- CTA/Accent: `#0369A1`
- Background: `#F0FDFA`
- Text: `#134E4A`
- Heading font: `Cinzel` with `Noto Sans SC` fallback
- Body font: `Josefin Sans` with `Noto Sans SC` fallback
- Mono font: `IBM Plex Mono`

## Layout Rules
- Workspaces are operational surfaces with clear rails and strong section headers.
- Use glass cards with visible borders in light mode; no low-opacity white-on-white treatment.
- Prefer two-column workstation layouts on desktop and one-column collapse on tablet/mobile.
- Floating navigation and fixed controls must preserve edge spacing and never cover content.
- Avoid horizontal scrolling on mobile.

## Interaction Rules
- No emoji icons. SVG only, from a single icon family.
- All interactive controls must expose pointer, hover, and focus-visible states.
- Hover states may adjust color, border, shadow, or opacity, but must not shift layout.
- Use 150-300ms transitions.
- Animate at most one or two key surfaces per view.
- Respect `prefers-reduced-motion`.

## Accessibility Rules
- Text contrast must meet 4.5:1 minimum for body copy.
- Color is never the only status indicator.
- Errors must be announced with `aria-live` or `role="alert"`.
- All form inputs require labels.
- Focus styles must remain visible across all workspace modes.

## Frontend Architecture Rules
- Components render only.
- Feature hooks and use-case helpers orchestrate workflow.
- Store slices keep state, not protocol shaping.
- Network and response normalization stay in data/access layers.
- Page-specific visual deviations must be documented in `design-system/pages/*.md`.

## Anti-patterns
- No “hero landing page” composition inside the authenticated workspace.
- No heavy parallax, scroll-jacking, or decorative motion noise.
- No mixing multiple icon families.
- No weak gray text on pale glass surfaces.
- No ad-hoc local color constants inside components.
