import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, retry, timeout, timer } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface HealthStatus {
  status: string;
  service: string;
  environment: string;
  database_mode: string;
  state_store_mode: string;
  gemini_configured: boolean;
  gemini_model?: string;
  mcp_enabled: boolean;
}

export interface MCPTool {
  name: string;
  server: string;
  description: string;
  input_schema: Record<string, unknown>;
}

export interface TraceStep {
  node: string;
  action: string;
  detail: string;
  timestamp: string;
}

export interface CodeArtifact {
  objective: string;
  snippet: string;
  inspector_verdict: string;
}

export interface ErrorDetail {
  code: string;
  status_code: number;
  worker: string;
  model: string;
  title: string;
  message: string;
  suggestion: string;
  retries: number;
  timestamp: string;
  raw_details?: string;
}

export interface AgentRunResponse {
  thread_id: string;
  objective: string;
  final_response: string;
  trace: TraceStep[];
  completed_workers: string[];
  research_notes: string[];
  code_artifacts: CodeArtifact[];
  tool_results: Record<string, unknown>[];
  errors?: string[];
  structured_errors?: ErrorDetail[];
  state_backend: string;
  gemini_model?: string;
}

@Injectable({ providedIn: 'root' })
export class HelmApiService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  getHealth(): Observable<HealthStatus> {
    return this.http.get<HealthStatus>(`${this.baseUrl}/health`);
  }

  getTools(): Observable<MCPTool[]> {
    return this.http.get<MCPTool[]>(`${this.baseUrl}/tools`);
  }

  runAgent(objective: string, maxIterations = 3): Observable<AgentRunResponse> {
    return this.http
      .post<AgentRunResponse>(`${this.baseUrl}/agents/run`, {
        objective,
        max_iterations: maxIterations,
      })
      .pipe(
        timeout({ each: 45000 }),
        retry({
          count: 3,
          delay: (error, retryCount) => {
            // Retry transient network dropouts, 502 Bad Gateway, 503 Unavailable, 504 Timeout
            if (
              error.status === 0 ||
              error.status === 502 ||
              error.status === 503 ||
              error.status === 504
            ) {
              return timer(retryCount * 1000);
            }
            throw error;
          },
        })
      );
  }
}
