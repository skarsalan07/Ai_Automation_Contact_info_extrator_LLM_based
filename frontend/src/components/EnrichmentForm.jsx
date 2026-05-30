import React, { useState } from 'react'

export default function EnrichmentForm({ onSubmit, onShowAll, loading }) {
  const [websiteName, setWebsiteName] = useState('')
  const [url, setUrl] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    const cleanUrl = (url || '').trim()
    if (!cleanUrl) return
    onSubmit({ url: cleanUrl, website_name: websiteName.trim() })
  }

  return (
    <form className="card" onSubmit={handleSubmit}>
      <div className="form-row">
        <div>
          <label htmlFor="website-name">Website Name (optional)</label>
          <input
            id="website-name"
            type="text"
            placeholder="e.g. Stripe"
            value={websiteName}
            onChange={(e) => setWebsiteName(e.target.value)}
            disabled={loading}
          />
        </div>
        <div>
          <label htmlFor="url">Website URL</label>
          <input
            id="url"
            type="url"
            placeholder="https://example.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
            disabled={loading}
          />
        </div>
      </div>
      <div className="actions">
        <button type="submit" className="primary" disabled={loading || !url.trim()}>
          {loading ? <><span className="spinner" /> Enriching…</> : 'Enrich'}
        </button>
        <button type="button" className="ghost" onClick={onShowAll} disabled={loading}>
          Show All Results
        </button>
      </div>
    </form>
  )
}
