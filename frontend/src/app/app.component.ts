import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  template: `
    <div class="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      <header class="border-b border-slate-800 bg-slate-900/70 backdrop-blur">
        <div class="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <span
              class="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-sky-500/15 border border-sky-400/30 text-sky-400 font-bold"
            >
              H
            </span>
            <div>
              <h1 class="text-lg font-semibold tracking-tight text-white">Helm</h1>
              <p class="text-xs text-slate-400">
                Multi-Agent Orchestration • LangGraph • Gemini • MCP
              </p>
            </div>
          </div>
          <span
            class="rounded-full bg-emerald-500/10 border border-emerald-500/30 px-3 py-1 text-xs font-medium text-emerald-300"
          >
            Scale-to-Zero Cloud Native
          </span>
        </div>
      </header>

      <main class="flex-1 max-w-7xl w-full mx-auto px-6 py-8">
        <router-outlet></router-outlet>
      </main>
    </div>
  `,
})
export class AppComponent {}
