import React from 'react'

export default function SkeletonLoader({ rows = 4 }) {
  return (
    <div className="result-grid" aria-hidden="true">
      {Array.from({ length: rows * 2 }).map((_, i) => (
        <div className="field" key={i}>
          <div className="skeleton" style={{ height: 10, width: '40%', marginBottom: 10 }} />
          <div className="skeleton" style={{ height: 14, width: '90%' }} />
        </div>
      ))}
    </div>
  )
}
