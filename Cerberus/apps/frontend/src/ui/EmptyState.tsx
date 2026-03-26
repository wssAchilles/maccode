type Props = {
  title: string
  body: string
}

export function EmptyState({ title, body }: Props) {
  return (
    <div className="empty-state" role="status">
      <p className="empty-state-title">{title}</p>
      <p className="empty-state-body">{body}</p>
    </div>
  )
}
