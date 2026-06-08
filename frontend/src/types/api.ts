/** API response types */

export interface User {
  id: string;
  email: string;
  name: string;
  role: "user" | "admin";
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface SourceReference {
  chunk_id: string;
  document_name: string;
  content_preview: string;
  category: string | null;
  relevance_score: number;
}

export interface ChatMessage {
  id: string;
  query: string;
  response: string;
  confidence: number;
  sources: SourceReference[];
  module_used: string | null;
  model_used: string;
  latency_ms: number;
  created_at: string;
  isStreaming?: boolean;
}

export interface Document {
  id: string;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  status: "pending" | "processing" | "completed" | "failed";
  total_chunks: number;
  metadata_json: Record<string, unknown>;
  user_id: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentList {
  documents: Document[];
  total: number;
  page: number;
  page_size: number;
}

export interface TrainingDashboard {
  total_documents: number;
  total_chunks: number;
  total_embeddings: number;
  categories_covered: string[];
  categories_missing: string[];
  coverage_percentage: number;
  duplicate_count: number;
  avg_chunk_size: number;
  retrieval_confidence_avg: number;
  weak_areas: string[];
}

export interface CategoryCoverage {
  category: string;
  chunk_count: number;
  coverage_score: number;
  quality_score: number;
  status: "strong" | "adequate" | "weak" | "missing";
}

export interface TrainingRecommendation {
  priority: "high" | "medium" | "low";
  category: string;
  recommendation: string;
  action: string;
  details: string;
}

export interface SystemStats {
  total_users: number;
  total_documents: number;
  total_chunks: number;
  total_queries: number;
  total_feedback: number;
  storage_used_mb: number;
  vector_db_status: string;
  avg_confidence: number;
  active_ingestion_jobs: number;
}

export interface FeedbackAnalytics {
  total_feedback: number;
  correct_count: number;
  partial_count: number;
  wrong_count: number;
  accuracy_rate: number;
}

export interface PluginInfo {
  name: string;
  version: string;
  description: string;
  capabilities: string[];
}

export interface ITXResponse {
  content: string;
  confidence: number;
  metadata: Record<string, unknown>;
}

export interface ContextChunk {
  source: string;
  category: string;
  relevance: number;
  preview: string;
}

export interface GenerateResponse {
  artifact_type: string;
  content: string;
  filename: string;
  context_used: ContextChunk[];
  model: string;
  latency_ms: number;
}

export interface GeneratedArtifact {
  filename: string;
  download_name: string;
  size_bytes: number;
  created_at: string;
  type: string;
}
