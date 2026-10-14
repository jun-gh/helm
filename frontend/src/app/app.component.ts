import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  template: `
    <div class="min-h-screen flex flex-col bg-[#F5F5F5] text-[#303841]">
      <header class="border-b border-[#76ABAE]/30 bg-[#F5F5F5]/90 backdrop-blur sticky top-0 z-50 shadow-xs">
        <div class="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div class="flex items-center gap-3">
            <span
              class="inline-flex h-9 w-9 items-center justify-center rounded-lg bg-[#FF5722] text-white font-black text-base shadow-sm"
            >
              H
            </span>
            <div>
              <h1 class="text-lg font-bold tracking-tight text-[#303841]">Helm</h1>
              <p class="text-xs text-[#303841]/75 font-medium">
                Multi-Agent Orchestration • LangGraph • Gemini • MCP
              </p>
            </div>
          </div>
          <span
            class="rounded-full bg-[#76ABAE]/15 border border-[#76ABAE]/40 px-3.5 py-1 text-xs font-semibold text-[#303841] shadow-2xs"
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
