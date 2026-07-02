import apiClient from './client'

export type InspectStats = {
  job_id?: string
  running?: boolean
  round?: number
  threads?: number
  total?: number
  deleted?: number
  matched?: number
  synced?: number
  failed?: number
  skipped?: number
  rounds_done?: number
  total_deleted?: number
  total_synced?: number
  total_failed?: number
  started_at?: string
  updated_at?: string
  finished_at?: string
  [key: string]: unknown
}

export type InspectState = {
  enabled: boolean
  stats?: InspectStats
  logs?: Array<{ time: string; text: string; level?: string }>
}

export const inspectApi = {
  getState() {
    return apiClient.get<any, { inspect: InspectState }>('/api/inspect')
  },
  start(threads?: number) {
    return apiClient.post<any, { inspect: InspectState }>(
      '/api/inspect/start',
      threads != null ? { threads } : {},
    )
  },
  stop() {
    return apiClient.post<any, { inspect: InspectState }>('/api/inspect/stop')
  },
}
