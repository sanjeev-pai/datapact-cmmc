export interface Mapping {
  id: string
  org_id: string
  practice_id: string
  datapact_contract_id: string
  datapact_contract_name: string | null
  created_at: string
  updated_at: string
}

export interface MappingListResponse {
  items: Mapping[]
  total: number
}

export interface MappingCreate {
  practice_id: string
  datapact_contract_id: string
  datapact_contract_name?: string
}

export interface Contract {
  id: string
  title: string
  description?: string
  status?: string
  parties?: string[]
  created_at?: string
  updated_at?: string
}

export interface ContractListResponse {
  items: Contract[]
  total: number
}

export interface SyncResult {
  practice_id: string
  status: string
  message: string | null
  compliance: Record<string, unknown> | null
}

export interface SyncResultsResponse {
  results: SyncResult[]
}

export interface SyncLog {
  id: string
  org_id: string
  assessment_id: string | null
  practice_id: string | null
  status: string
  error_message: string | null
  created_at: string
}

export interface SyncLogListResponse {
  items: SyncLog[]
  total: number
}
