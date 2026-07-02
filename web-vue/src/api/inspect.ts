import apiClient from './client'

export type InspectStats = {
  job_id?: string
  running?: boolean
  total?: number
  deleted?: number
  matched?: number
  synced?: number
  failed?: number
  skipped?: number
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
  start() {
    return apiClient.post<any, { inspect: InspectState }>('/api/inspect/start')
  },
  stop() {
    return apiClient.post<any, { inspect: InspectState }>('/api/inspect/stop')
  },
}
