import React from 'react'
import EmptyState from './EmptyState.jsx'

function safe(v) {
  if (v === null || v === undefined || v === '') return '—'
  return v
}

export default function ResultsTable({ rows }) {
  if (!Array.isArray(rows) || rows.length === 0) {
    return <EmptyState title="No saved results" hint="Enrich a few prospects, then come back." />
  }
  return (
    <div className="card" style={{ overflowX: 'auto' }}>
      <table className="results-table">
        <thead>
          <tr>
            <th>Company</th>
            <th>Website</th>
            <th>Email(s)</th>
            <th>Phone</th>
            <th>Core Service</th>
            <th>Target Customer</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id || `${r.source_url}-${r.created_at || ''}`}>
              <td>{safe(r.company_name)}</td>
              <td>{safe(r.website_name)}</td>
              <td>
                {Array.isArray(r.mail) && r.mail.length > 0
                  ? r.mail.map((m) => <span key={m} className="email-pill">{m}</span>)
                  : '—'}
              </td>
              <td>{safe(r.mobile_number)}</td>
              <td>{safe(r.core_service)}</td>
              <td>{safe(r.target_customer)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
