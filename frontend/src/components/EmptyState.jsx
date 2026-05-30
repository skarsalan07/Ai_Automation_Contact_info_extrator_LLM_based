import React from 'react'

export default function EmptyState({ title = 'No results yet', hint = 'Enrich a company to see its profile here.' }) {
  return (
    <div className="empty-state">
      <div className="icon">📭</div>
      <div style={{ fontWeight: 600, color: 'var(--text)' }}>{title}</div>
      <div style={{ marginTop: 6 }}>{hint}</div>
    </div>
  )
}
