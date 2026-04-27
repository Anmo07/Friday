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

export interface AgentOutput {
  agent: string;
  output: Record<string, any>;
  latency_ms: number;
  cached: boolean;
}

export interface Viewpoint {
  stance: "supporting" | "questioning" | "neutral" | "opposing";
  summary: string;
  confidence: number;
}

export interface PerspectiveData {
  viewpoints: Viewpoint[];
  consensus_level: string;
}

export interface ContradictionData {
  contradictions_found: string[];
  consistency_score: number;
  conflicting_claims: string[];
}

export interface CacheStats {
  query_cache: { size: number; hits: number; misses: number; hit_rate: number };
  agent_cache: { size: number; hits: number; misses: number; hit_rate: number };
  embedding_cache: { size: number; hits: number; misses: number; hit_rate: number };
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
  _cached?: boolean;
  latency_ms?: number;
  depth_level?: 1 | 2 | 3;
  cache_stats?: CacheStats;
  assistant_mode?: "assistant" | "verification";
  intent?: "control" | "news" | "verification" | "chat" | "interrupt";
  action?: string;
  executed?: boolean;
  requires_confirmation?: boolean;
  interrupted?: boolean;
  topic?: string;
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
  status: "session" | "assistant" | "processing" | "complete" | "alert" | "error" | "interrupted" | "agent_update" | "voice_command";
  stage?: string;
  progress?: number;
  message?: string;
  data?: QueryResponse | AlertItem | AgentOutput | Record<string, any>;
  error?: { message: string } | string;
  transcription?: string;
  has_audio?: boolean;
  greeting?: string;
  period?: "morning" | "evening" | "neutral";
  mode?: "assistant" | "verification";
  intent?: "control" | "news" | "verification" | "chat" | "interrupt";
  agent?: string;
  depth_level?: number;
  agent_outputs?: Record<string, any>;
}
