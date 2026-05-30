const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function jsonOrThrow(resp) {
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`
    try {
      const body = await resp.json()
      if (body?.detail) detail = body.detail
    } catch (_) {}
    throw new Error(detail)
  }
  return resp.json()
}

export async function enrichUrl({ url, website_name }) {
  const resp = await fetch(`${BASE}/enrich`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, website_name: website_name || null }),
  })
  return jsonOrThrow(resp)
}

export async function fetchResults() {
  const resp = await fetch(`${BASE}/results`)
  return jsonOrThrow(resp)
}
