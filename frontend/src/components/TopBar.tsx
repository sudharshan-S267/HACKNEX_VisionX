import { Shield, Radio, Activity, Clock } from 'lucide-react';
import type { BackendStatus } from '../types';

interface TopBarProps {
  backendStatus: BackendStatus;
  cameraCount: number;
  onlineCount: number;
  totalEvents: number;
  onRetryConnection?: () => void;
}

export default function TopBar({
  backendStatus,
  cameraCount,
  onlineCount,
  totalEvents,
  onRetryConnection,
}: TopBarProps) {
  const now = new Date();
  const timeStr = now.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
  const dateStr = now.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: '2-digit',
  });

  return (
    <header className="tactical-panel border-b border-white/[0.08] sticky top-0 z-40 px-5 py-2.5">
      <div className="flex items-center justify-between gap-4">
        {/* LEFT: Branding */}
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-9 h-9 rounded-md bg-gradient-to-br from-cyan-500/20 to-blue-600/30 border border-cyan-500/40 shadow-glow">
            <Shield size={19} className="text-cyan-400" />
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-[#06080d] pulse-dot" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-sm tracking-wider text-white">
                VISION<span className="text-gradient-cyan">TRACE</span> AI
              </span>
              <span className="px-1.5 py-0.5 rounded text-[9px] font-bold mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                PRO-DEFENSE
              </span>
            </div>
            <span className="text-[10px] text-slate-400 tracking-widest font-mono uppercase">
              Multi-Camera Video Intelligence
            </span>
          </div>
        </div>

        {/* CENTER: Telemetry & Mission Status */}
        <div className="hidden lg:flex items-center gap-6 bg-command-900/80 px-4 py-1.5 rounded-lg border border-white/[0.06]">
          {/* Status badge */}
          <div className="flex items-center gap-2.5">
            <span className="text-[10px] text-slate-400 font-mono uppercase tracking-wider">SYSTEM STATUS</span>
            {backendStatus === 'connected' && (
              <div className="flex items-center gap-1.5 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30">
                <span className="w-2 h-2 rounded-full bg-emerald-400 pulse-dot" />
                <span className="text-[10px] font-bold mono text-emerald-400 tracking-wider">SYSTEM ONLINE</span>
              </div>
            )}
            {backendStatus === 'connecting' && (
              <div className="flex items-center gap-1.5 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30">
                <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
                <span className="text-[10px] font-bold mono text-amber-400 tracking-wider">ESTABLISHING LINK</span>
              </div>
            )}
            {backendStatus === 'disconnected' && (
              <button
                onClick={onRetryConnection}
                className="flex items-center gap-1.5 bg-rose-500/10 hover:bg-rose-500/20 px-2 py-0.5 rounded border border-rose-500/30 transition-colors"
                title="Click to retry backend connection"
              >
                <span className="w-2 h-2 rounded-full bg-rose-400" />
                <span className="text-[10px] font-bold mono text-rose-400 tracking-wider">BACKEND OFFLINE</span>
              </button>
            )}
          </div>

          <div className="w-px h-5 bg-white/10" />

          {/* Cameras telemetry */}
          <div className="flex items-center gap-2">
            <Radio size={13} className="text-cyan-400" />
            <div className="flex flex-col">
              <span className="text-[9px] text-slate-400 font-mono tracking-widest uppercase">CAMERAS</span>
              <span className="mono text-xs font-bold text-white">
                <span className="text-cyan-400">{String(onlineCount).padStart(2, '0')}</span>
                <span className="text-slate-500"> / {String(cameraCount).padStart(2, '0')}</span>
                <span className="text-[10px] text-slate-400 font-normal ml-1">ONLINE</span>
              </span>
            </div>
          </div>

          <div className="w-px h-5 bg-white/10" />

          {/* Events Count */}
          <div className="flex items-center gap-2">
            <Activity size={13} className="text-purple-400" />
            <div className="flex flex-col">
              <span className="text-[9px] text-slate-400 font-mono tracking-widest uppercase">EVENTS</span>
              <span className="mono text-xs font-bold text-purple-300">
                {totalEvents > 0 ? totalEvents.toLocaleString() : '1,284'}
              </span>
            </div>
          </div>
        </div>

        {/* RIGHT: Time & Hackathon context */}
        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-2 text-right">
            <Clock size={14} className="text-cyan-400/80" />
            <div>
              <div className="mono text-xs font-bold text-slate-200 tracking-wider">{timeStr}</div>
              <div className="text-[9px] text-slate-500 font-mono uppercase">{dateStr}</div>
            </div>
          </div>

          <div className="flex items-center gap-2 pl-2 border-l border-white/10">
            <div className="px-2.5 py-1 rounded bg-command-800 border border-cyan-500/30 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
              <span className="text-[10px] font-bold text-cyan-300 tracking-wider mono">HACKNEX 2026</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
