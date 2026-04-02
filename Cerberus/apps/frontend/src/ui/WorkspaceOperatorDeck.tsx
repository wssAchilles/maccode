import type { WorkspaceOperatorDeckSectionModel } from '../view-models/workbench'
import { cn } from '../lib/cn'
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
    <div className={deckClass}>
      {sections.map((section, index) => (
        <RevealGroup
          key={section.id}
          revealIndex={index}
          className={cn(
            'od-shell',
            section.visualPriority === 'hero' ? 'od-shell-hero' : '',
            layout === 'rail' && section.visualPriority === 'hero' ? 'od-shell-span' : '',
          )}
        >
          <MotionSurface className={cn('od-surface', section.accent ? `od-surface-${section.accent}` : '')} mode="panel">
            <GlassPanel className={cn('stack-sm od-card', section.accent ? `od-card-${section.accent}` : '')} tone="subtle">
              <div className="ids-group">
                <div className="sp-head">
                  <p className="subtle-label">{section.title}</p>
                  {section.postureLabel ? <p className="subtle-label">{section.postureLabel}</p> : null}
                </div>
                {section.summary ? <p className="panel-caption">{section.summary}</p> : null}
              </div>
              <DataList items={section.items} dense />
            </GlassPanel>
          </MotionSurface>
        </RevealGroup>
      ))}
    </div>
  )
}
