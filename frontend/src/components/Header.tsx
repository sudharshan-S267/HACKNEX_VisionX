import { Shield, Wifi, WifiOff, AlertCircle } from 'lucide-react';
import type { BackendStatus } from '../types';

interface HeaderProps {
  backendStatus: BackendStatus;
  cameraCount: number;
  onlineCount: number;
}

export default function Header({ backendStatus, cameraCount, onlineCount }: HeaderProps) {
  const now = new Date();
  const timeStr = now.toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
  const dateStr = now.toLocaleDateString('en-US', {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: '2-digit',
  });

  return (
    <header className="glass border-b border-subtle sticky top-0 z-50">
      <div className="flex items-center justify-between px-6 py-3">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-blue-600 to-violet-600 flex items-center justify-center shadow-glow">
              <Shield size={18} className="text-white" />
            </div>
            <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-400 border border-[#0a0a0f] pulse-dot" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white tracking-tight">
              Vision<span className="text-gradient">Trace</span> AI
            </h1>
            <p className="text-[10px] text-slate-500 font-medium tracking-widest uppercase">
              Multi-Camera Video Intelligence
            </p>
          </div>
        </div>

        {/* Center status bar */}
        <div className="hidden md:flex items-center gap-6">
          {/* Camera count */}
          <div className="flex flex-col items-center">
            <span className="mono text-lg font-semibold text-blue-400 leading-none">
              {String(onlineCount).padStart(2, '0')}
              <span className="text-slate-600">/{String(cameraCount).padStart(2, '0')}</span>
            </span>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider mt-0.5">Cameras Online</span>
          </div>

          <div className="w-px h-8 bg-white/5" />

          {/* System time */}
          <div className="flex flex-col items-center">
            <span className="mono text-lg font-semibold text-white leading-none">{timeStr}</span>
            <span className="text-[10px] text-slate-500 uppercase tracking-wider mt-0.5">{dateStr}</span>
          </div>

          <div className="w-px h-8 bg-white/5" />

          {/* Backend status */}
          <div className="flex flex-col items-center">
            {backendStatus === 'connected' && (
              <>
                <div className="flex items-center gap-1.5">
                  <Wifi size={13} className="text-emerald-400" />
                  <span className="text-emerald-400 text-xs font-semibold">ONLINE</span>
                </div>
                <span className="text-[10px] text-slate-500 uppercase tracking-wider mt-0.5">Backend API</span>
              </>
            )}
            {backendStatus === 'connecting' && (
              <>
                <div className="flex items-center gap-1.5">
                  <AlertCircle size={13} className="text-yellow-400 animate-pulse" />
                  <span className="text-yellow-400 text-xs font-semibold">CONNECTING</span>
                </div>
                <span className="text-[10px] text-slate-500 uppercase tracking-wider mt-0.5">Backend API</span>
              </>
            )}
            {backendStatus === 'disconnected' && (
              <>
                <div className="flex items-center gap-1.5">
                  <WifiOff size={13} className="text-red-400" />
                  <span className="text-red-400 text-xs font-semibold">OFFLINE</span>
                </div>
                <span className="text-[10px] text-slate-500 uppercase tracking-wider mt-0.5">Backend API</span>
              </>
            )}
          </div>
        </div>

        {/* Right tag */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-slate-600 font-mono uppercase tracking-widest hidden sm:block">
            HACKNEX · 2026
          </span>
          <div className="px-2 py-1 rounded bg-blue-500/10 border border-blue-500/20">
            <span className="text-blue-400 text-[10px] font-semibold mono">v1.0.0</span>
          </div>
        </div>
      </div>
    </header>
  );
}
