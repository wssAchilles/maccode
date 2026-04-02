import type { WorkspaceOperatorDeckSectionModel } from '../view-models/workbench'
import { DataList } from './DataList'
import { GlassPanel } from './GlassPanel'

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
      {sections.map((section) => (
        <GlassPanel key={section.id} className="stack-sm" tone="subtle">
          <div className="ids-group">
            <p className="subtle-label">{section.title}</p>
            {section.summary ? <p className="panel-caption">{section.summary}</p> : null}
          </div>
          <DataList items={section.items} dense />
        </GlassPanel>
      ))}
    </div>
  )
}
