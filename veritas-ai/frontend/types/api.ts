export interface Source {
  url: string;
  credibility_score: number;
  type: "official" | "media" | "social" | "unknown";
}

export interface ConfidenceBreakdown {
  authority: number;
  agreement: number;
  bias: number;
}

export interface Explanation {
  why_true: string[];
  why_false: string[];
  confidence_breakdown: ConfidenceBreakdown;
}

export interface QueryResponse {
  query: string;
  summary: string;
  facts: string[];
  sources: Source[];
  contradictions: string[];
  fake_probability: number;
  confidence_score: number;
  truth_score: number;
  status: "verified" | "likely_false" | "uncertain";
  explanation?: Explanation | null;
  timestamp: string;
}

export interface AlertItem {
  alert_type: string;
  severity: "low" | "medium" | "high";
  message: string;
  timestamp: string;
}

export interface HistoryEntry {
  id: number;
  timestamp: string;
  query: string;
  status: string;
  truth_score: number;
  summary: string;
}

export interface HistoryResponse {
  status: "success";
  items: HistoryEntry[];
}

export interface WebSocketMessage {
  status: "idle" | "processing" | "complete" | "alert" | "error";
  data?: QueryResponse | AlertItem;
  message?: string;
  progress?: number;
  error?: { message: string };
}
