import React from 'react'

export default function LoadingState({ label = 'Enriching prospect…' }) {
  return (
    <div className="card" role="status" aria-live="polite">
      <div className="row">
        <span className="spinner" />
        <strong>{label}</strong>
      </div>
      <div className="muted" style={{ marginTop: 8 }}>
        Discovering pages, scraping content, and generating insights. This typically takes 8–20 seconds.
      </div>
      <div className="progress-bar"><div /></div>
    </div>
  )
}
