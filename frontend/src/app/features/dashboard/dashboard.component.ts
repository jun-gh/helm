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
            <div class="flex items-center justify-between">
              <h2 class="text-lg font-semibold text-white">Multi-Worker Mission Steering</h2>
              <span class="rounded-full bg-sky-500/10 border border-sky-500/30 px-3 py-0.5 text-xs text-sky-300 font-mono">
                Supervisor • Researcher • Coder
              </span>
            </div>
            <p class="text-sm text-slate-400 mt-1">
              Gemini analyzes the objective and steers work dynamically across specialized
              Worker nodes with bound MCP tools before producing the final synthesis.
            </p>
          </div>

          <!-- Quick Presets -->
          <div class="flex flex-wrap gap-2 text-xs">
            <span class="text-slate-400 self-center">Presets:</span>
            <button
              type="button"
              (click)="setPreset('Research and implement JWT authentication token validation')"
              class="rounded-md border border-slate-700 bg-slate-800/60 px-2.5 py-1 text-slate-300 hover:border-sky-500 hover:text-white transition"
            >
              JWT Auth (Research + Code)
            </button>
            <button
              type="button"
              (click)="setPreset('Audit scale-to-zero Cloud Run strategy and write database session manager')"
              class="rounded-md border border-slate-700 bg-slate-800/60 px-2.5 py-1 text-slate-300 hover:border-sky-500 hover:text-white transition"
            >
              Cloud Run & DB Session
            </button>
            <button
              type="button"
              (click)="setPreset('Compare MCP Stdio vs SSE transports for serverless agents')"
              class="rounded-md border border-slate-700 bg-slate-800/60 px-2.5 py-1 text-slate-300 hover:border-sky-500 hover:text-white transition"
            >
              MCP Transport Research
            </button>
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
                placeholder="e.g., Research and design a JWT auth validator in Python..."
                class="w-full rounded-lg border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:border-sky-400 focus:outline-none"
              ></textarea>
            </div>
            <div class="flex items-center gap-4">
              <button
                type="submit"
                [disabled]="isRunning() || !objectiveInput.trim()"
                class="inline-flex items-center justify-center rounded-lg bg-sky-500 px-5 py-2.5 text-sm font-semibold text-slate-950 hover:bg-sky-400 disabled:opacity-50 transition"
              >
                {{ isRunning() ? 'Orchestrating Specialists...' : 'Launch Orchestration Run' }}
              </button>
              @if (isRunning()) {
                <span class="text-xs text-sky-400 animate-pulse">
                  Supervisor evaluating routes & executing workers...
                </span>
              }
            </div>
          </form>

          @if (runResult(); as result) {
            <div class="space-y-5 pt-4 border-t border-slate-800">
              <div class="flex items-center justify-between text-xs text-slate-400">
                <span>Thread ID: <code class="text-sky-300 font-mono">{{ result.thread_id }}</code></span>
                <span>Active Specialists:
                  <strong class="text-slate-200 uppercase font-mono">
                    {{ result.completed_workers.join(', ') || 'diagnostic' }}
                  </strong>
                </span>
              </div>

              <!-- Supervisor Final Synthesis -->
              <div class="rounded-lg border border-slate-800 bg-slate-950 p-4">
                <h3 class="text-xs font-semibold uppercase tracking-wider text-sky-400 mb-2">
                  Supervisor Executive Synthesis
                </h3>
                <div class="whitespace-pre-wrap text-sm text-slate-200 font-sans leading-relaxed">
                  {{ result.final_response }}
                </div>
              </div>

              <!-- Research Notes if present -->
              @if (result.research_notes && result.research_notes.length > 0) {
                <div class="rounded-lg border border-purple-900/40 bg-purple-950/20 p-4 space-y-2">
                  <h3 class="text-xs font-semibold uppercase tracking-wider text-purple-400">
                    Researcher Worker Findings
                  </h3>
                  @for (note of result.research_notes; track $index) {
                    <div class="whitespace-pre-wrap text-xs text-purple-200/90 font-mono">
                      {{ note }}
                    </div>
                  }
                </div>
              }

              <!-- Code Artifacts if present -->
              @if (result.code_artifacts && result.code_artifacts.length > 0) {
                <div class="rounded-lg border border-emerald-900/40 bg-emerald-950/20 p-4 space-y-2">
                  <div class="flex items-center justify-between">
                    <h3 class="text-xs font-semibold uppercase tracking-wider text-emerald-400">
                      Coder Worker Scaffolding
                    </h3>
                    <span class="text-[0.7rem] rounded bg-emerald-950 border border-emerald-800/60 px-2 py-0.5 text-emerald-300 font-mono">
                      {{ result.code_artifacts[0].inspector_verdict }}
                    </span>
                  </div>
                  <pre class="overflow-x-auto rounded bg-slate-950 p-3 text-xs text-emerald-300 font-mono"><code>{{ result.code_artifacts[0].snippet }}</code></pre>
                </div>
              }

              <!-- Execution Trace Steps -->
              <div class="space-y-2">
                <h3 class="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  LangGraph Multi-Worker Trace
                </h3>
                @for (step of result.trace; track step.timestamp) {
                  <div
                    class="flex items-start justify-between rounded-lg border border-slate-800/80 bg-slate-950/60 px-4 py-2.5 text-xs"
                  >
                    <div class="flex items-center gap-2">
                      <span
                        [ngClass]="getNodeBadgeClass(step.node)"
                        class="px-2 py-0.5 rounded text-[0.7rem] font-bold uppercase tracking-wider border font-mono"
                      >
                        {{ step.node }}
                      </span>
                      <span class="text-slate-300">{{ step.detail }}</span>
                    </div>
                    <span class="text-slate-500 font-mono text-[0.7rem]">{{ step.action }}</span>
                  </div>
                }
              </div>
            </div>
          }
        </section>

        <!-- Registered MCP Tools Sidebar -->
        <aside class="rounded-xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
          <div>
            <h2 class="text-lg font-semibold text-white">MCP Tool Registry</h2>
            <p class="text-sm text-slate-400">
              Tools available to the Supervisor, Researcher, and Coder workers.
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

  objectiveInput = 'Research and implement JWT authentication token validation';

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

  setPreset(presetText: string): void {
    this.objectiveInput = presetText;
  }

  getNodeBadgeClass(node: string): string {
    switch (node.toLowerCase()) {
      case 'supervisor':
        return 'bg-sky-500/15 border-sky-400/30 text-sky-300';
      case 'researcher':
        return 'bg-purple-500/15 border-purple-400/30 text-purple-300';
      case 'coder':
        return 'bg-emerald-500/15 border-emerald-400/30 text-emerald-300';
      default:
        return 'bg-slate-800 border-slate-700 text-slate-300';
    }
  }

  dispatchObjective(): void {
    if (!this.objectiveInput.trim() || this.isRunning()) {
      return;
    }
    this.isRunning.set(true);
    this.api.runAgent(this.objectiveInput.trim(), 3).subscribe({
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
