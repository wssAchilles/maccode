import type { WorkspaceOperatorDeckSectionModel } from '../view-models/workbench'
import { cn } from '../lib/cn'
import { DataList } from './DataList'
import { GlassPanel } from './GlassPanel'
import { MotionSurface } from './MotionSurface'
import { RevealGroup } from './RevealGroup'

type Props = {
  sections: WorkspaceOperatorDeckSectionModel[]
  layout?: 'grid' | 'stack'
}

export function WorkspaceOperatorDeck({ sections, layout = 'grid' }: Props) {
  if (sections.length === 0) {
    return null
  }

  return (
    <div className={layout === 'stack' ? 'stack-sm' : 'ids-grid'}>
      {sections.map((section, index) => (
        <RevealGroup key={section.id} revealIndex={index} className={cn(section.visualPriority === 'hero' ? 'od-shell-hero' : '')}>
          <MotionSurface mode="panel">
            <GlassPanel className="stack-sm" tone="subtle">
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
