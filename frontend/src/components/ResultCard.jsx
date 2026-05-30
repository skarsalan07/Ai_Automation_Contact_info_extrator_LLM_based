import React from 'react'

function Value({ value }) {
  if (value === null || value === undefined || value === '') {
    return <span className="value empty">Not available</span>
  }
  return <span className="value">{value}</span>
}

function MailList({ mails }) {
  if (!Array.isArray(mails) || mails.length === 0) {
    return <span className="value empty">Not available</span>
  }
  return (
    <div className="value">
      {mails.map((m) => (
        <span key={m} className="email-pill">{m}</span>
      ))}
    </div>
  )
}

export default function ResultCard({ profile }) {
  if (!profile) return null
  const p = profile || {}
  return (
    <div className="card">
      <div className="row" style={{ marginBottom: 12 }}>
        <h2 style={{ margin: 0, fontSize: 20 }}>{p.company_name || 'Unknown company'}</h2>
        <span className="spacer" />
        <span className="muted">{p.website_name || ''}</span>
      </div>
      <div className="result-grid">
        <div className="field">
          <div className="label">Website Name</div>
          <Value value={p.website_name} />
        </div>
        <div className="field">
          <div className="label">Company Name</div>
          <Value value={p.company_name} />
        </div>
        <div className="field wide">
          <div className="label">Emails</div>
          <MailList mails={p.mail} />
        </div>
        <div className="field">
          <div className="label">Phone</div>
          <Value value={p.mobile_number} />
        </div>
        <div className="field">
          <div className="label">Address</div>
          <Value value={p.address} />
        </div>
        <div className="field wide">
          <div className="label">Core Service</div>
          <Value value={p.core_service} />
        </div>
        <div className="field">
          <div className="label">Target Customer</div>
          <Value value={p.target_customer} />
        </div>
        <div className="field">
          <div className="label">Probable Pain Point</div>
          <Value value={p.probable_pain_point} />
        </div>
        <div className="field wide">
          <div className="label">Outreach Opener</div>
          <Value value={p.outreach_opener} />
        </div>
      </div>
    </div>
  )
}
