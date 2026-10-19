import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  AgentRunResponse,
  ErrorDetail,
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
      <!-- Telemetry Status Cards (2nd: 76ABAE surfaces/borders / 3rd: 303841 typography) -->
      <section class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="rounded-xl border border-[#76ABAE]/35 bg-white p-4 shadow-xs">
          <span class="text-xs uppercase tracking-wider text-[#76ABAE] font-bold">API Status</span>
          <div class="mt-2 text-base font-bold text-[#303841]">
            {{ health()?.status || 'connecting...' }}
          </div>
        </div>
        <div class="rounded-xl border border-[#76ABAE]/35 bg-white p-4 shadow-xs">
          <span class="text-xs uppercase tracking-wider text-[#76ABAE] font-bold">Relational DB</span>
          <div class="mt-2 text-base font-bold text-[#303841]">
            {{ health()?.database_mode || 'sqlite-local' }}
          </div>
        </div>
        <div class="rounded-xl border border-[#76ABAE]/35 bg-white p-4 shadow-xs">
          <span class="text-xs uppercase tracking-wider text-[#76ABAE] font-bold">State & Memory</span>
          <div class="mt-2 text-base font-bold text-[#303841]">
            {{ health()?.state_store_mode || 'in-memory' }}
          </div>
        </div>
        <div class="rounded-xl border border-[#76ABAE]/35 bg-white p-4 shadow-xs">
          <div class="flex items-center justify-between">
            <span class="text-xs uppercase tracking-wider text-[#76ABAE] font-bold">LLM</span>
            <span
              class="inline-flex items-center rounded-full px-2 py-0.5 text-[0.65rem] font-bold"
              [ngClass]="health()?.gemini_configured ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'"
            >
              {{ health()?.gemini_configured ? 'Configured' : 'Fallback' }}
            </span>
          </div>
          <div class="mt-2 text-base font-bold text-[#303841] font-mono truncate" [title]="health()?.gemini_model || ''">
            {{ health()?.gemini_model || 'gemini-3.8-flash' }}
          </div>
        </div>
      </section>

      <!-- Main Steering Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Mission Dispatch Panel -->
        <section
          class="lg:col-span-2 rounded-xl border border-[#76ABAE]/35 bg-white p-6 space-y-5 shadow-xs"
        >
          <div>
            <div class="flex flex-wrap items-center justify-between gap-2">
              <h2 class="text-lg font-bold text-[#303841]">Multi-Worker Mission Steering</h2>
              <div class="flex items-center gap-2">
                <span
                  class="rounded-full bg-[#76ABAE]/15 border border-[#76ABAE]/40 px-2.5 py-0.5 text-xs text-[#303841] font-mono font-semibold"
                  title="Active Gemini Model loaded from environment"
                >
                  🤖 {{ health()?.gemini_model || 'gemini-3.8-flash' }}
                </span>
                <span class="rounded-full bg-[#76ABAE]/15 border border-[#76ABAE]/40 px-3 py-0.5 text-xs text-[#303841] font-mono font-semibold">
                  Supervisor • Researcher • Coder
                </span>
              </div>
            </div>
            <p class="text-sm text-[#303841]/75 mt-1 font-medium">
              Gemini analyzes the objective and steers work dynamically across specialized
              Worker nodes with bound MCP tools before producing the final synthesis.
            </p>
          </div>

          <!-- Quick Presets -->
          <div class="flex flex-wrap gap-2 text-xs">
            <span class="text-[#303841] font-bold self-center">Presets:</span>
            <button
              type="button"
              (click)="setPreset('Research and implement JWT authentication token validation')"
              class="rounded-md border border-[#76ABAE]/40 bg-[#F5F5F5] px-2.5 py-1 text-[#303841] hover:border-[#FF5722] hover:bg-[#FF5722]/10 transition shadow-2xs font-medium"
            >
              JWT Auth (Research + Code)
            </button>
            <button
              type="button"
              (click)="setPreset('Audit scale-to-zero serverless strategy and write database session manager')"
              class="rounded-md border border-[#76ABAE]/40 bg-[#F5F5F5] px-2.5 py-1 text-[#303841] hover:border-[#FF5722] hover:bg-[#FF5722]/10 transition shadow-2xs font-medium"
            >
              Serverless & DB Session
            </button>
            <button
              type="button"
              (click)="setPreset('Compare MCP Stdio vs SSE transports for serverless agents')"
              class="rounded-md border border-[#76ABAE]/40 bg-[#F5F5F5] px-2.5 py-1 text-[#303841] hover:border-[#FF5722] hover:bg-[#FF5722]/10 transition shadow-2xs font-medium"
            >
              MCP Transport Research
            </button>
          </div>

          <form (ngSubmit)="dispatchObjective()" class="space-y-4">
            <div>
              <label for="objective" class="block text-xs font-bold text-[#303841] mb-2 uppercase tracking-wide">
                Mission Objective
              </label>
              <textarea
                id="objective"
                name="objective"
                [(ngModel)]="objectiveInput"
                rows="3"
                placeholder="e.g., Research and design a JWT auth validator in Python..."
                class="w-full rounded-lg border border-[#76ABAE]/40 bg-[#F5F5F5] px-4 py-3 text-sm text-[#303841] placeholder-[#303841]/45 focus:border-[#76ABAE] focus:bg-white focus:outline-none transition shadow-2xs"
              ></textarea>
            </div>
            <div class="flex items-center gap-4">
              <button
                type="submit"
                [disabled]="isRunning() || !objectiveInput.trim()"
                class="inline-flex items-center justify-center rounded-lg bg-[#FF5722] px-5 py-2.5 text-sm font-bold text-white hover:bg-[#e64a19] active:scale-[0.99] disabled:opacity-50 transition shadow-xs"
              >
                {{ isRunning() ? 'Orchestrating Specialists...' : 'Launch Orchestration Run' }}
              </button>
              @if (isRunning()) {
                <span class="text-xs text-[#76ABAE] animate-pulse font-mono font-semibold">
                  Supervisor routing with {{ health()?.gemini_model || 'Gemini' }} & executing workers...
                </span>
              }
            </div>
          </form>

          <!-- Network/Server Error Alert Banner -->
          @if (httpErrorMessage()) {
            <div class="mt-4 rounded-xl border border-[#FF5722] bg-[#FF5722]/10 p-4 space-y-2">
              <div class="flex items-center gap-2 text-[#FF5722] font-bold text-xs uppercase tracking-wider">
                <span>⚠️ Orchestration Request Notice</span>
              </div>
              <p class="text-xs text-[#303841] font-mono whitespace-pre-wrap">{{ httpErrorMessage() }}</p>
              <p class="text-[0.7rem] text-[#303841]/75 font-medium">
                Tip: Google Gemini free-tier clusters occasionally experience temporary traffic spikes. Helm will automatically fail-fast to local intelligence, or you can retry in a moment.
              </p>
            </div>
          }

          @if (runResult(); as result) {
            <div class="space-y-5 pt-4 border-t border-[#76ABAE]/30">
              <!-- Structured AI Diagnostics Card -->
              @if (result.structured_errors && result.structured_errors.length > 0) {
                <div class="rounded-xl border border-amber-400 bg-amber-50/80 p-5 space-y-4 shadow-xs">
                  <div class="flex flex-wrap items-center justify-between gap-2 border-b border-amber-200/80 pb-3">
                    <div class="flex items-center gap-2">
                      <span class="text-lg">🛡️</span>
                      <div>
                        <h3 class="text-xs font-bold uppercase tracking-wider text-amber-950">
                          Resilient AI Execution & Quota Diagnostics
                        </h3>
                        <p class="text-[0.72rem] text-amber-900/80">
                          Helm executed 3-retry exponential backoff and safely recovered using domain intelligence.
                        </p>
                      </div>
                    </div>
                    <span class="inline-flex items-center gap-1 rounded-full bg-emerald-100 border border-emerald-300 px-2.5 py-0.5 text-[0.68rem] font-bold text-emerald-900">
                      <span>✓</span> Self-Healing Active
                    </span>
                  </div>

                  <div class="space-y-3">
                    @for (diag of result.structured_errors; track $index) {
                      <div class="rounded-lg border border-amber-300/70 bg-white p-4 space-y-2.5 shadow-2xs">
                        <div class="flex flex-wrap items-center justify-between gap-2">
                          <div class="flex items-center gap-2">
                            <span
                              class="rounded-md border px-2 py-0.5 text-[0.68rem] font-bold font-mono uppercase tracking-wider"
                              [ngClass]="getErrorBadgeClass(diag.code)"
                            >
                              {{ getErrorIcon(diag.code) }} {{ diag.code }} ({{ diag.status_code }})
                            </span>
                            <span class="text-xs font-bold text-[#303841]">{{ diag.title }}</span>
                          </div>
                          <div class="flex items-center gap-2 text-[0.7rem] font-mono text-[#303841]/80">
                            <span class="rounded bg-[#76ABAE]/15 border border-[#76ABAE]/35 px-2 py-0.5 text-[#303841] font-semibold">
                              {{ diag.worker }}
                            </span>
                            <span class="rounded bg-gray-100 border border-gray-200 px-2 py-0.5 text-[#303841] font-semibold">
                              🔄 {{ diag.retries }}/3 Retries Attempted
                            </span>
                          </div>
                        </div>

                        <p class="text-xs text-[#303841]/90 leading-relaxed font-sans">
                          {{ diag.message }}
                        </p>

                        <!-- Actionable Suggestion Box -->
                        <div class="rounded-md bg-[#76ABAE]/10 border border-[#76ABAE]/30 p-2.5 flex items-start gap-2 text-xs text-[#303841]">
                          <span class="text-sm leading-none mt-0.5">💡</span>
                          <div class="space-y-1">
                            <span class="font-bold text-[0.72rem] uppercase tracking-wider text-[#303841]">
                              Recommended Action:
                            </span>
                            <p class="text-xs leading-relaxed text-[#303841]/90">
                              {{ diag.suggestion }}
                            </p>
                          </div>
                        </div>

                        <!-- Technical Details Toggle -->
                        @if (diag.raw_details) {
                          <div>
                            <button
                              type="button"
                              (click)="toggleErrorDetail($index)"
                              class="text-[0.7rem] text-[#76ABAE] hover:text-[#FF5722] font-semibold font-mono flex items-center gap-1 transition"
                            >
                              <span>{{ isErrorExpanded($index) ? '▼ Hide' : '▶ Show' }} Raw Provider Telemetry</span>
                            </button>
                            @if (isErrorExpanded($index)) {
                              <pre class="mt-2 overflow-x-auto rounded bg-[#303841] p-2.5 text-[0.7rem] text-[#F5F5F5] font-mono border border-[#303841]"><code>{{ diag.raw_details }}</code></pre>
                            }
                          </div>
                        }
                      </div>
                    }
                  </div>
                </div>
              } @else if (result.errors && result.errors.length > 0) {
                <!-- Fallback Warning Banner for unstructured notices -->
                <div class="rounded-xl border border-[#FF5722] bg-[#FF5722]/10 p-4 space-y-2">
                  <div class="flex items-center gap-2 text-[#FF5722] font-bold text-xs uppercase tracking-wider">
                    <span>⚠️ AI Provider Warning / Quota Notice</span>
                  </div>
                  <div class="space-y-1">
                    @for (err of result.errors; track $index) {
                      <div class="text-xs text-[#303841] font-mono">{{ err }}</div>
                    }
                  </div>
                  <p class="text-[0.7rem] text-[#303841]/75 pt-1 font-medium">
                    Note: Helm automatically recovered using domain intelligence and executed all specialized workers without failing.
                  </p>
                </div>
              }

              <div class="flex flex-wrap items-center justify-between gap-3 text-xs text-[#303841]/75 font-medium">
                <span>Thread ID: <code class="text-[#303841] font-mono font-bold">{{ result.thread_id }}</code></span>
                <span>Active Model:
                  <strong class="text-[#303841] font-mono font-bold">
                    {{ result.gemini_model || health()?.gemini_model || 'gemini-3.8-flash' }}
                  </strong>
                </span>
                <span>Active Specialists:
                  <strong class="text-[#303841] uppercase font-mono">
                    {{ result.completed_workers.join(', ') || 'diagnostic' }}
                  </strong>
                </span>
              </div>

              <!-- Supervisor Final Synthesis -->
              <div class="rounded-lg border border-[#76ABAE]/35 bg-[#F5F5F5] p-4 shadow-2xs">
                <h3 class="text-xs font-bold uppercase tracking-wider text-[#76ABAE] mb-2">
                  Supervisor Executive Synthesis
                </h3>
                <div class="whitespace-pre-wrap text-sm text-[#303841] font-sans leading-relaxed">
                  {{ result.final_response }}
                </div>
              </div>

              <!-- Research Notes if present -->
              @if (result.research_notes && result.research_notes.length > 0) {
                <div class="rounded-lg border border-[#76ABAE]/40 bg-[#76ABAE]/10 p-4 space-y-2 shadow-2xs">
                  <h3 class="text-xs font-bold uppercase tracking-wider text-[#303841]">
                    Researcher Worker Findings
                  </h3>
                  @for (note of result.research_notes; track $index) {
                    <div class="whitespace-pre-wrap text-xs text-[#303841] font-mono">
                      {{ note }}
                    </div>
                  }
                </div>
              }

              <!-- Code Artifacts if present -->
              @if (result.code_artifacts && result.code_artifacts.length > 0) {
                <div class="rounded-lg border border-[#76ABAE]/35 bg-white p-4 space-y-2 shadow-2xs">
                  <div class="flex items-center justify-between">
                    <h3 class="text-xs font-bold uppercase tracking-wider text-[#303841]">
                      Coder Worker Scaffolding
                    </h3>
                    <span class="text-[0.7rem] rounded bg-[#76ABAE]/15 border border-[#76ABAE]/40 px-2 py-0.5 text-[#303841] font-mono font-semibold">
                      {{ result.code_artifacts[0].inspector_verdict }}
                    </span>
                  </div>
                  <pre class="overflow-x-auto rounded bg-[#303841] p-3 text-xs text-[#F5F5F5] font-mono border border-[#303841] shadow-inner"><code>{{ result.code_artifacts[0].snippet }}</code></pre>
                </div>
              }

              <!-- Execution Trace Steps -->
              <div class="space-y-2">
                <h3 class="text-xs font-bold uppercase tracking-wider text-[#303841]">
                  LangGraph Multi-Worker Trace
                </h3>
                @for (step of result.trace; track step.timestamp) {
                  <div
                    class="flex items-start justify-between rounded-lg border border-[#76ABAE]/25 bg-[#F5F5F5] px-4 py-2.5 text-xs shadow-2xs"
                  >
                    <div class="flex items-center gap-2">
                      <span
                        [ngClass]="getNodeBadgeClass(step.node)"
                        class="px-2 py-0.5 rounded text-[0.7rem] font-bold uppercase tracking-wider border font-mono"
                      >
                        {{ step.node }}
                      </span>
                      <span class="text-[#303841] font-medium">{{ step.detail }}</span>
                    </div>
                    <span class="text-[#76ABAE] font-mono text-[0.7rem]">{{ step.action }}</span>
                  </div>
                }
              </div>
            </div>
          }
        </section>

        <!-- Sidebar: Registered MCP Tools -->
        <aside class="space-y-6">
          <!-- Registered MCP Tools -->
          <div class="rounded-xl border border-[#76ABAE]/35 bg-white p-6 space-y-4 shadow-xs">
            <div>
              <h2 class="text-lg font-bold text-[#303841]">MCP Tool Registry</h2>
              <p class="text-sm text-[#303841]/75 font-medium">
                Tools available to the Supervisor, Researcher, and Coder workers.
              </p>
            </div>

            <div class="space-y-3">
              @for (tool of tools(); track tool.name) {
                <div class="rounded-lg border border-[#76ABAE]/25 bg-[#F5F5F5] p-3.5 space-y-1 shadow-2xs">
                  <div class="flex items-center justify-between">
                    <span class="text-sm font-mono font-bold text-[#303841]">{{ tool.name }}</span>
                    <span
                      class="rounded bg-[#76ABAE]/15 border border-[#76ABAE]/40 px-2 py-0.5 text-[0.7rem] text-[#303841] font-mono font-medium"
                    >
                      {{ tool.server }}
                    </span>
                  </div>
                  <p class="text-xs text-[#303841]/75 font-medium">{{ tool.description }}</p>
                </div>
              } @empty {
                <p class="text-xs text-[#303841]/70">Start the FastAPI backend to inspect MCP tools.</p>
              }
            </div>
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
  readonly httpErrorMessage = signal<string | null>(null);
  readonly expandedErrorIndices = signal<Set<number>>(new Set<number>());

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
    this.httpErrorMessage.set(null);
  }

  toggleErrorDetail(index: number): void {
    const next = new Set(this.expandedErrorIndices());
    if (next.has(index)) {
      next.delete(index);
    } else {
      next.add(index);
    }
    this.expandedErrorIndices.set(next);
  }

  isErrorExpanded(index: number): boolean {
    return this.expandedErrorIndices().has(index);
  }

  getErrorBadgeClass(code: string): string {
    switch (code) {
      case 'QUOTA_EXCEEDED':
      case 'SERVICE_UNAVAILABLE':
        return 'bg-amber-100 text-amber-900 border-amber-300';
      case 'AUTH_ERROR':
        return 'bg-rose-100 text-rose-900 border-rose-300';
      case 'TIMEOUT':
        return 'bg-orange-100 text-orange-900 border-orange-300';
      default:
        return 'bg-red-100 text-red-900 border-red-300';
    }
  }

  getErrorIcon(code: string): string {
    switch (code) {
      case 'QUOTA_EXCEEDED':
        return '⏳';
      case 'SERVICE_UNAVAILABLE':
        return '⚡';
      case 'AUTH_ERROR':
        return '🔒';
      case 'TIMEOUT':
        return '⏱️';
      default:
        return '⚠️';
    }
  }

  getNodeBadgeClass(node: string): string {
    switch (node.toLowerCase()) {
      case 'supervisor':
        return 'bg-[#76ABAE]/20 border-[#76ABAE]/60 text-[#303841]';
      case 'researcher':
        return 'bg-[#76ABAE] border-[#76ABAE] text-white';
      case 'coder':
        return 'bg-[#FF5722] border-[#FF5722] text-white';
      default:
        return 'bg-[#F5F5F5] border-[#76ABAE]/35 text-[#303841]';
    }
  }

  dispatchObjective(): void {
    if (!this.objectiveInput.trim() || this.isRunning()) {
      return;
    }
    this.isRunning.set(true);
    this.httpErrorMessage.set(null);

    this.api.runAgent(this.objectiveInput.trim(), 3).subscribe({
      next: (res) => {
        this.runResult.set(res);
        this.isRunning.set(false);
      },
      error: (err) => {
        let detail =
          err.error?.detail || err.message || 'Server error occurred during agent orchestration.';
        if (err.name === 'TimeoutError' || err.message?.includes('Timeout')) {
          detail =
            'Request timed out after 45s (3 retry attempts). The upstream AI cluster is experiencing heavy demand. Please retry in a moment.';
        }
        this.httpErrorMessage.set(detail);
        this.isRunning.set(false);
      },
    });
  }
}
