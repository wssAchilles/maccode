import { describe, expect, it } from 'vitest'

import { WORKSPACE_GROUPS, WORKSPACE_MODELS, WORKSPACE_PANELS_BY_WORKSPACE } from './workbench'

describe('workbench workspace registry', () => {
  it('registers the seven web workspaces in order', () => {
    expect(WORKSPACE_MODELS.map((item) => item.id)).toEqual([
      'overview',
      'market',
      'book',
      'strategy',
      'execution',
      'inference',
      'health',
    ])
  })

  it('covers every workspace exactly once across rail groups', () => {
    const groupedIds = WORKSPACE_GROUPS.flatMap((group) => group.items.map((item) => item.id))

    expect(groupedIds).toHaveLength(WORKSPACE_MODELS.length)
    expect(new Set(groupedIds)).toEqual(new Set(WORKSPACE_MODELS.map((item) => item.id)))
  })

  it('defines a home panel plus focused subpages for each workspace', () => {
    for (const workspace of WORKSPACE_MODELS) {
      const panels = WORKSPACE_PANELS_BY_WORKSPACE[workspace.id]
      expect(panels[0]?.id).toBe('home')
      expect(new Set(panels.map((panel) => panel.id)).size).toBe(panels.length)
      expect(panels.length).toBeGreaterThanOrEqual(4)
      expect(panels.length).toBeLessThanOrEqual(6)
    }
  })
})
