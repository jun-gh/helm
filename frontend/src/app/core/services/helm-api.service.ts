import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, timeout } from 'rxjs';
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
  state_backend: string;
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
      .pipe(timeout({ each: 35000 }));
  }
}
