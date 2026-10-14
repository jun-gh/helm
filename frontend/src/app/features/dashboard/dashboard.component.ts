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
            {{ health()?.state_store_mode || 'firestore' }}
          </div>
        </div>
        <div class="rounded-xl border border-[#76ABAE]/35 bg-white p-4 shadow-xs">
          <span class="text-xs uppercase tracking-wider text-[#76ABAE] font-bold">Gemini LLM</span>
          <div class="mt-2 text-base font-bold text-[#303841]">
            {{ health()?.gemini_configured ? ('Active (' + (health()?.gemini_model || 'Gemini') + ')') : 'Fallback Mode' }}
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
            <div class="flex items-center justify-between">
              <h2 class="text-lg font-bold text-[#303841]">Multi-Worker Mission Steering</h2>
              <span class="rounded-full bg-[#76ABAE]/15 border border-[#76ABAE]/40 px-3 py-0.5 text-xs text-[#303841] font-mono font-semibold">
                Supervisor • Researcher • Coder
              </span>
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
              (click)="setPreset('Audit scale-to-zero Cloud Run strategy and write database session manager')"
              class="rounded-md border border-[#76ABAE]/40 bg-[#F5F5F5] px-2.5 py-1 text-[#303841] hover:border-[#FF5722] hover:bg-[#FF5722]/10 transition shadow-2xs font-medium"
            >
              Cloud Run & DB Session
            </button>
            <button
              type="button"
              (click)="setPreset('Compare MCP Stdio vs SSE transports for serverless agents')"
              class="rounded-md border border-[#76ABAE]/40 bg-[#F5F5F5] px-2.5 py-1 text-[#303841] hover:border-[#FF5722] hover:bg-[#FF5722]/10 transition shadow-2xs font-medium"
            >
              MCP Transport Research
            </button>
          </div>

          <!-- Network/Server Error Alert Banner -->
          @if (httpErrorMessage()) {
            <div class="rounded-xl border border-[#FF5722] bg-[#FF5722]/10 p-4 space-y-1">
              <div class="flex items-center gap-2 text-[#FF5722] font-bold text-xs uppercase tracking-wider">
                <span>⚠️ Connection / Server Error</span>
              </div>
              <p class="text-xs text-[#303841] font-mono whitespace-pre-wrap">{{ httpErrorMessage() }}</p>
            </div>
          }

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
                  Supervisor evaluating routes & executing workers...
                </span>
              }
            </div>
          </form>

          @if (runResult(); as result) {
            <div class="space-y-5 pt-4 border-t border-[#76ABAE]/30">
              <!-- Provider / Quota Warning Banner -->
              @if (result.errors && result.errors.length > 0) {
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

              <div class="flex items-center justify-between text-xs text-[#303841]/75 font-medium">
                <span>Thread ID: <code class="text-[#303841] font-mono font-bold">{{ result.thread_id }}</code></span>
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

        <!-- Registered MCP Tools Sidebar -->
        <aside class="rounded-xl border border-[#76ABAE]/35 bg-white p-6 space-y-4 shadow-xs">
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
        const detail = err.error?.detail || err.message || 'Server error occurred during agent orchestration.';
        this.httpErrorMessage.set(detail);
        this.isRunning.set(false);
      },
    });
  }
}
