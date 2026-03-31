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
    <dl className={dense ? 'data-list data-list-dense' : 'data-list'}>
      {items.map((item) => (
        <div key={item.id} className="data-list-row">
          <dt className="data-list-label">{item.label}</dt>
          <dd
            className={
              item.tone === 'accent'
                ? 'data-list-value data-list-value-accent'
                : item.tone === 'positive'
                  ? 'data-list-value data-list-value-positive'
                  : item.tone === 'negative'
                    ? 'data-list-value data-list-value-negative'
                    : item.tone === 'muted'
                      ? 'data-list-value data-list-value-muted'
                      : 'data-list-value'
            }
          >
            {item.value}
          </dd>
        </div>
      ))}
    </dl>
  )
}
