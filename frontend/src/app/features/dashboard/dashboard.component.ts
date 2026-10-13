import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  AgentRunResponse,
  HealthStatus,
  HelmApiService,
  MCPTool,
} from '../../core/services/helm-api.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="space-y-8">
      <!-- Telemetry Status Cards -->
      <section class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <span class="text-xs uppercase tracking-wider text-slate-400">API Status</span>
          <div class="mt-2 text-base font-semibold text-emerald-400">
            {{ health()?.status || 'connecting...' }}
          </div>
        </div>
        <div class="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <span class="text-xs uppercase tracking-wider text-slate-400">Relational DB</span>
          <div class="mt-2 text-base font-semibold text-sky-300">
            {{ health()?.database_mode || 'sqlite-local' }}
          </div>
        </div>
        <div class="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <span class="text-xs uppercase tracking-wider text-slate-400">State & Memory</span>
          <div class="mt-2 text-base font-semibold text-indigo-300">
            {{ health()?.state_store_mode || 'firestore' }}
          </div>
        </div>
        <div class="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <span class="text-xs uppercase tracking-wider text-slate-400">Gemini LLM</span>
          <div class="mt-2 text-base font-semibold text-amber-300">
            {{ health()?.gemini_configured ? 'Active (Gemini 2.5)' : 'Fallback Mode' }}
          </div>
        </div>
      </section>

      <!-- Main Steering Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Mission Dispatch Panel -->
        <section
          class="lg:col-span-2 rounded-xl border border-slate-800 bg-slate-900/60 p-6 space-y-5"
        >
          <div>
            <h2 class="text-lg font-semibold text-white">Steer Multi-Agent Workflow</h2>
            <p class="text-sm text-slate-400">
              Dispatch an objective to the LangGraph Supervisor node. The supervisor coordinates
              MCP-equipped workers and checkpoints state to Firestore.
            </p>
          </div>

          <form (ngSubmit)="dispatchObjective()" class="space-y-4">
            <div>
              <label for="objective" class="block text-xs font-medium text-slate-300 mb-2">
                Mission Objective
              </label>
              <textarea
                id="objective"
                name="objective"
                [(ngModel)]="objectiveInput"
                rows="3"
                placeholder="e.g., Audit cluster health and create a multi-step rollout plan..."
                class="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:border-sky-400 focus:outline-none"
              ></textarea>
            </div>
            <button
              type="submit"
              [disabled]="isRunning() || !objectiveInput.trim()"
              class="inline-flex items-center justify-center rounded-lg bg-sky-500 px-5 py-2.5 text-sm font-semibold text-slate-950 hover:bg-sky-400 disabled:opacity-50 transition"
            >
              {{ isRunning() ? 'Orchestrating Agents...' : 'Launch Orchestration Run' }}
            </button>
          </form>

          @if (runResult(); as result) {
            <div class="space-y-4 pt-4 border-t border-slate-800">
              <div class="flex items-center justify-between text-xs text-slate-400">
                <span>Thread ID: <code class="text-sky-300">{{ result.thread_id }}</code></span>
                <span>State Store: {{ result.state_backend }}</span>
              </div>

              <div class="rounded-lg border border-slate-800 bg-slate-950 p-4">
                <h3 class="text-xs font-semibold uppercase tracking-wider text-sky-400 mb-2">
                  Supervisor Synthesis
                </h3>
                <pre class="whitespace-pre-wrap text-sm text-slate-200 font-mono">{{
                  result.final_response
                }}</pre>
              </div>

              <div class="space-y-2">
                <h3 class="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  LangGraph Execution Trace
                </h3>
                @for (step of result.trace; track step.timestamp) {
                  <div
                    class="flex items-start justify-between rounded-lg border border-slate-800/80 bg-slate-950/60 px-4 py-2.5 text-xs"
                  >
                    <div>
                      <span class="font-semibold text-sky-300 uppercase">{{ step.node }}</span>
                      <span class="mx-2 text-slate-600">•</span>
                      <span class="text-slate-300">{{ step.detail }}</span>
                    </div>
                    <span class="text-slate-500 font-mono">{{ step.action }}</span>
                  </div>
                }
              </div>
            </div>
          }
        </section>

        <!-- Registered MCP Tools Sidebar -->
        <aside class="rounded-xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
          <div>
            <h2 class="text-lg font-semibold text-white">MCP Tool Layer</h2>
            <p class="text-sm text-slate-400">
              Model Context Protocol tools bound to Helm worker nodes.
            </p>
          </div>

          <div class="space-y-3">
            @for (tool of tools(); track tool.name) {
              <div class="rounded-lg border border-slate-800 bg-slate-950 p-3.5 space-y-1">
                <div class="flex items-center justify-between">
                  <span class="text-sm font-mono font-semibold text-sky-300">{{ tool.name }}</span>
                  <span
                    class="rounded bg-slate-800 px-2 py-0.5 text-[0.7rem] text-slate-400 font-mono"
                  >
                    {{ tool.server }}
                  </span>
                </div>
                <p class="text-xs text-slate-400">{{ tool.description }}</p>
              </div>
            } @empty {
              <p class="text-xs text-slate-500">Start the FastAPI backend to inspect MCP tools.</p>
            }
          </div>
        </aside>
      </div>
    </div>
  `,
})
export class DashboardComponent implements OnInit {
  private readonly api = inject(HelmApiService);

  readonly health = signal<HealthStatus | null>(null);
  readonly tools = signal<MCPTool[]>([]);
  readonly runResult = signal<AgentRunResponse | null>(null);
  readonly isRunning = signal<boolean>(false);

  objectiveInput = 'Verify multi-agent readiness and generate a zero-cost Cloud Run deployment plan';

  ngOnInit(): void {
    this.api.getHealth().subscribe({
      next: (res) => this.health.set(res),
      error: () => this.health.set(null),
    });
    this.api.getTools().subscribe({
      next: (res) => this.tools.set(res),
      error: () => this.tools.set([]),
    });
  }

  dispatchObjective(): void {
    if (!this.objectiveInput.trim() || this.isRunning()) {
      return;
    }
    this.isRunning.set(true);
    this.api.runAgent(this.objectiveInput.trim()).subscribe({
      next: (res) => {
        this.runResult.set(res);
        this.isRunning.set(false);
      },
      error: () => {
        this.isRunning.set(false);
      },
    });
  }
}
