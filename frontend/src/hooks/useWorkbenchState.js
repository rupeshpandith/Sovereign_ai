/**
 * useWorkbenchState — persistent workbench state via localStorage.
 *
 * Persisted keys (all prefixed sovereign_wb_):
 *   documents   — list of uploaded documents
 *   selectedId  — currently selected document_id
 *   goal        — goal textarea value
 *   run         — last agent run handle { agent_run_id, status }
 *   runStatus   — last full status response (steps, evidence, flags, etc.)
 *
 * On mount: state is restored from localStorage.
 * On mount with a non-terminal run: the status is re-fetched from the backend
 *   so the user sees the latest result immediately without re-running.
 */
import { useEffect, useRef, useState, useCallback } from 'react'
import { getRunStatus } from '../api/agent'

const PREFIX = 'sovereign_wb_'
const TERMINAL = ['awaiting_approval', 'approved', 'rejected', 'complete', 'failed']

function load(key, fallback) {
  try {
    const raw = localStorage.getItem(PREFIX + key)
    return raw !== null ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

function save(key, value) {
  try {
    if (value === null || value === undefined) {
      localStorage.removeItem(PREFIX + key)
    } else {
      localStorage.setItem(PREFIX + key, JSON.stringify(value))
    }
  } catch {
    // Storage full or private mode — silently ignore
  }
}

const DEFAULT_GOAL = 'Assess pump P-204 vibration against SOP-17 and draft an approval note.'

export function useWorkbenchState() {
  // ── State ──────────────────────────────────────────────────────────────────
  const [documents, setDocumentsRaw] = useState(() => load('documents', []))
  const [selectedId, setSelectedIdRaw] = useState(() => load('selectedId', null))
  const [goal, setGoalRaw] = useState(() => load('goal', DEFAULT_GOAL))
  const [run, setRunRaw] = useState(() => load('run', null))
  const [runStatus, setRunStatusRaw] = useState(() => load('runStatus', null))
  const [runError, setRunError] = useState(null)

  // ── Persisting setters ─────────────────────────────────────────────────────
  const setDocuments = useCallback((updater) => {
    setDocumentsRaw((prev) => {
      const next = typeof updater === 'function' ? updater(prev) : updater
      save('documents', next)
      return next
    })
  }, [])

  const setSelectedId = useCallback((id) => {
    setSelectedIdRaw(id)
    save('selectedId', id)
  }, [])

  const setGoal = useCallback((g) => {
    setGoalRaw(g)
    save('goal', g)
  }, [])

  const setRun = useCallback((r) => {
    setRunRaw(r)
    save('run', r)
  }, [])

  const setRunStatus = useCallback((s) => {
    setRunStatusRaw((prev) => {
      const next = typeof s === 'function' ? s(prev) : s
      save('runStatus', next)
      return next
    })
  }, [])

  // On mount: re-fetch status if last run was non-terminal
  // and fetch the document list from the backend to fill any localStorage gaps.
  const hydrated = useRef(false)
  useEffect(() => {
    if (hydrated.current) return
    hydrated.current = true

    // 1. Re-fetch run status if it wasn't terminal when we last closed the tab
    const storedRun = load('run', null)
    const storedStatus = load('runStatus', null)
    if (storedRun?.agent_run_id) {
      const lastStatus = storedStatus?.status
      if (!lastStatus || !TERMINAL.includes(lastStatus)) {
        getRunStatus(storedRun.agent_run_id)
          .then((s) => setRunStatus(s))
          .catch(() => {/* backend offline — keep stored */})
      }
    }

    // 2. Fetch document list from backend and merge with localStorage
    //    so uploads are visible even if localStorage was cleared.
    import('../api/client').then(({ api }) => {
      api.get('/documents')
        .then(({ data }) => {
          if (!Array.isArray(data) || data.length === 0) return
          setDocuments((prev) => {
            const existingIds = new Set(prev.map((d) => d.document_id))
            const incoming = data.filter((d) => !existingIds.has(d.document_id))
            if (incoming.length === 0) return prev
            return [...incoming, ...prev]
          })
        })
        .catch(() => {/* not critical — localStorage already has the list */})
    })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return {
    // State
    documents,
    selectedId,
    goal,
    run,
    runStatus,
    runError,
    // Setters
    setDocuments,
    setSelectedId,
    setGoal,
    setRun,
    setRunStatus,
    setRunError,
  }
}
