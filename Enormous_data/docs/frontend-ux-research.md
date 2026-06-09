# Frontend UX Research Notes

## Scope

This note records the interaction design direction for the React front end of Enormous Data Dashboard. The goal is a production-grade analytics cockpit for Spark e-commerce behavior analysis, not a coursework-only page.

## Sources Reviewed

- Anime.js: lightweight timeline, stagger, and state-transition animation patterns.
- React Bits: copyable, composable React interaction primitives with parameterized motion.
- Telegram Web K: high-density navigation, instant switching, persistent status visibility, and compact operational controls.
- WCAG 2.2 and UI/UX Pro Max: focus visibility, target size, reduced motion, readable responsive layout, and dashboard-specific density.

## Design Decisions

1. Use a data-dense cockpit layout instead of a marketing-style hero-first site.
2. Keep persistent navigation visible on desktop, with a collapsed mode for focused analysis.
3. Group navigation by user workflow: core cockpit, intelligent analysis, data and operations.
4. Add a top context bar so the user always knows the current workflow and can jump to high-frequency modules.
5. Keep command search as the fastest global interaction path, with keyboard guidance and grouped result details.
6. Use Anime.js for short spatial transitions only: page entry, command palette entry, and staggered result reveal.
7. Respect `prefers-reduced-motion` globally so animation never becomes a requirement for comprehension.
8. Preserve 44px-plus targets for command, navigation, close, collapse, and mobile drawer controls.
9. Avoid decorative single-purpose animation; motion must communicate hierarchy, continuity, or response.
10. Ensure mobile behaves as an operational drawer, not a squeezed desktop sidebar.

## Implementation Mapping

- `frontend/src/components/layout/navigation.ts`: single source of truth for routes, labels, groups, details, and icons.
- `frontend/src/components/layout/AppShell.tsx`: grouped sidebar, collapsible desktop navigation, mobile drawer, top workflow bar.
- `frontend/src/components/layout/CommandPalette.tsx`: grouped command search with close action and shortcut footer.
- `frontend/src/styles/global.css`: neutral cockpit theme, responsive drawer behavior, focus states, reduced-motion guardrails, dense control styling.

## Next UX Modules

1. Add page-level filter bars with saved presets for behavior, conversion, lifecycle, and anomaly pages.
2. Add table affordances: sticky headers, row action drawer, copied identifiers, and density switching.
3. Add chart interaction states: click-to-focus, synchronized tooltip, empty-state explanation, and accessible tabular fallback.
4. Add background job feedback: toast/event center for Spark run lifecycle, errors, and generated artifact links.
