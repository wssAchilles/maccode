type Item = {
  id: string
  label: string
  value: string
  tone?: 'default' | 'muted' | 'accent' | 'positive' | 'negative'
}

type Props = {
  items: Item[]
  dense?: boolean
}

export function DataList({ items, dense = false }: Props) {
  return (
    <dl className={dense ? 'data-list dl-dense' : 'data-list'}>
      {items.map((item) => (
        <div key={item.id} className="dl-row">
          <dt className="dl-label">{item.label}</dt>
          <dd
            className={
              item.tone === 'accent'
                ? 'dl-value dl-value-accent'
                : item.tone === 'positive'
                  ? 'dl-value dl-value-positive'
                  : item.tone === 'negative'
                    ? 'dl-value dl-value-negative'
                    : item.tone === 'muted'
                      ? 'dl-value dl-value-muted'
                      : 'dl-value'
            }
          >
            {item.value}
          </dd>
        </div>
      ))}
    </dl>
  )
}
