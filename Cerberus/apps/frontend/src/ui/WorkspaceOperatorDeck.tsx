import type { CSSProperties } from 'react'

import type { WorkspaceOperatorDeckSectionModel } from '../view-models/workbench'
import { cn } from '../lib/cn'
import { accentVar } from './accent'
import { DataList } from './DataList'
import { GlassPanel } from './GlassPanel'
import { MotionSurface } from './MotionSurface'
import { RevealGroup } from './RevealGroup'

type Props = {
  sections: WorkspaceOperatorDeckSectionModel[]
  layout?: 'grid' | 'stack' | 'rail'
}

export function WorkspaceOperatorDeck({ sections, layout = 'grid' }: Props) {
  if (sections.length === 0) {
    return null
  }

  const deckClass =
    layout === 'stack'
      ? 'stack-sm'
      : layout === 'rail'
        ? 'od-rail'
        : 'ids-grid'

  return (
    <div className={deckClass} data-layout={layout}>
      {sections.map((section, index) => {
        const isHero = section.visualPriority === 'hero'
        const showSummary = isHero || layout !== 'rail'

        return (
        <RevealGroup
          key={section.id}
          revealIndex={index}
          className={cn('od-shell', layout === 'rail' && section.visualPriority === 'hero' ? 'od-shell-span' : '')}
          data-priority={isHero ? 'hero' : 'secondary'}
          style={
            section.accent
              ? ({
                  '--pa': accentVar(section.accent),
                } as CSSProperties)
              : undefined
          }
        >
          <MotionSurface className="od-surface" mode={isHero ? 'spotlight' : 'panel'}>
            <GlassPanel className={cn('stack-sm od-card', isHero ? 'od-card-hero' : 'od-card-secondary')} tone="subtle">
              <div className="ids-group">
                <div className="od-head">
                  <div className="od-copy">
                    <p className="subtle-label">{section.title}</p>
                    {showSummary ? <p className="od-summary">{section.summary}</p> : null}
                  </div>
                  {section.postureLabel ? <span className="od-posture">{section.postureLabel}</span> : null}
                </div>
              </div>
              <DataList items={section.items} dense />
            </GlassPanel>
          </MotionSurface>
        </RevealGroup>
        )
      })}
    </div>
  )
}
