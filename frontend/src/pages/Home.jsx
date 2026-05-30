import React, { useState } from 'react'
import EnrichmentForm from '../components/EnrichmentForm.jsx'
import LoadingState from '../components/LoadingState.jsx'
import SkeletonLoader from '../components/SkeletonLoader.jsx'
import ResultCard from '../components/ResultCard.jsx'
import ResultsTable from '../components/ResultsTable.jsx'
import EmptyState from '../components/EmptyState.jsx'
import { useToast } from '../components/Toast.jsx'
import { enrichUrl, fetchResults } from '../api.js'

export default function Home() {
  const toast = useToast()
  const [loading, setLoading] = useState(false)
  const [tableLoading, setTableLoading] = useState(false)
  const [profile, setProfile] = useState(null)
  const [rows, setRows] = useState(null)

  const handleEnrich = async ({ url, website_name }) => {
    setLoading(true)
    setProfile(null)
    try {
      const data = await enrichUrl({ url, website_name })
      setProfile(data)
      toast.push('Enrichment complete', 'success')
    } catch (e) {
      toast.push(`Enrichment failed: ${e.message}`, 'error', 6000)
    } finally {
      setLoading(false)
    }
  }

  const handleShowAll = async () => {
    setTableLoading(true)
    try {
      const data = await fetchResults()
      setRows(data)
      toast.push(`Loaded ${data.length} record(s)`, 'info')
    } catch (e) {
      toast.push(`Could not load results: ${e.message}`, 'error', 6000)
    } finally {
      setTableLoading(false)
    }
  }

  return (
    <div className="container">
      <div className="header">
        <h1>Prospect Research Agent</h1>
        <span className="badge">Groq · llama-3.3-70b</span>
      </div>

      <EnrichmentForm onSubmit={handleEnrich} onShowAll={handleShowAll} loading={loading} />

      <div className="section-title">Current Enrichment</div>
      {loading && <LoadingState />}
      {loading && (
        <div style={{ marginTop: 14 }}>
          <SkeletonLoader rows={4} />
        </div>
      )}
      {!loading && profile && <ResultCard profile={profile} />}
      {!loading && !profile && <EmptyState />}

      <div className="section-title">All Saved Results</div>
      {tableLoading ? (
        <SkeletonLoader rows={3} />
      ) : rows === null ? (
        <EmptyState title="Click 'Show All Results'" hint="…to load everything stored in the SQLite database." />
      ) : (
        <ResultsTable rows={rows} />
      )}
    </div>
  )
}
