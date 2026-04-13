import React from 'react';
import { SummaryData } from '../../shared/types';
import { ActionItemList } from '../ActionItemList';

export interface SummaryPanelProps {
  data?: SummaryData;
  isLoading: boolean;
  isError: boolean;
  onRetry?: () => void;
}

export const SummaryPanel: React.FC<SummaryPanelProps> = ({
  data,
  isLoading,
  isError,
  onRetry,
}) => {
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-4">
        <div className="w-12 h-12 border-2 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin" />
        <p className="font-mono text-xs text-cyan-400 uppercase tracking-widest animate-pulse">Analyzing_Semantics...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-6">
        <div className="text-red-500 font-mono text-xs uppercase tracking-widest animate-flicker">Neural_Link_Broken</div>
        {onRetry && (
          <button onClick={onRetry} className="tech-button border-red-500/50 text-red-400 hover:bg-red-500">
            Retry_Analysis
          </button>
        )}
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      {/* 摘要正文 */}
      <section className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="h-4 w-1 bg-cyan-500 shadow-[0_0_8px_#00f3ff]" />
          <h2 className="text-sm font-mono font-bold text-cyan-400 uppercase tracking-[0.2em]">01_Core_Summary</h2>
        </div>
        <div className="bg-white/5 border border-white/5 p-6 rounded-xl relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
            <svg className="w-20 h-20 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
            </svg>
          </div>
          <p className="text-white/80 leading-relaxed relative z-10 first-letter:text-3xl first-letter:font-black first-letter:text-cyan-400 first-letter:mr-1">
            {data.summary || 'DATA_NOT_FOUND'}
          </p>
        </div>
      </section>

      <div className="grid md:grid-cols-2 gap-8">
        {/* 關鍵點 */}
        <section className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="h-4 w-1 bg-magenta-500 shadow-[0_0_8px_#ff00ff]" />
            <h3 className="text-sm font-mono font-bold text-magenta-400 uppercase tracking-[0.2em]">02_Key_Points</h3>
          </div>
          <div className="bg-white/5 border border-white/5 p-6 rounded-xl h-full">
            <ul className="space-y-4">
              {data.key_points && data.key_points.length > 0 ? (
                data.key_points.map((point, index) => (
                  <li key={index} className="flex gap-3 group">
                    <span className="text-magenta-500/50 font-mono text-[10px] mt-1 group-hover:text-magenta-400 transition-colors">[{index + 1}]</span>
                    <span className="text-white/70 text-sm leading-snug">{point}</span>
                  </li>
                ))
              ) : (
                <li className="text-white/20 italic font-mono text-xs">VOID_ARRAY</li>
              )}
            </ul>
          </div>
        </section>

        {/* 行動項 */}
        <section className="space-y-4">
          <div className="flex items-center gap-3">
            <div className="h-4 w-1 bg-blue-500 shadow-[0_0_8px_#0066ff]" />
            <h3 className="text-sm font-mono font-bold text-blue-400 uppercase tracking-[0.2em]">03_Action_Items</h3>
          </div>
          <div className="bg-white/5 border border-white/5 p-6 rounded-xl h-full">
            <ActionItemList items={data.action_items || []} />
          </div>
        </section>
      </div>
    </div>
  );
};
