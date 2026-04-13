import React from 'react';
import { TranscriptSegment } from '../../shared/types';
import { TranscriptSegmentCard } from '../TranscriptSegmentCard';
import { useTranslationToggle } from '../../features/toggle-translation';
import { useTranscriptSearch } from '../../features/search-transcript';

export interface TranscriptPanelProps {
  data?: TranscriptSegment[];
  isLoading: boolean;
  isError: boolean;
  onRetry?: () => void;
}

export const TranscriptPanel: React.FC<TranscriptPanelProps> = ({
  data = [],
  isLoading,
  isError,
  onRetry,
}) => {
  const { showTranslation, toggleTranslation } = useTranslationToggle(true);
  const { searchQuery, setSearchQuery, filteredSegments } = useTranscriptSearch(data);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-4">
        <div className="w-12 h-12 border-2 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin" />
        <p className="font-mono text-xs text-cyan-400 uppercase tracking-widest animate-pulse">Scanning_Buffer...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-6">
        <div className="text-red-500 font-mono text-xs uppercase tracking-widest animate-flicker">Data_Retrieval_Error</div>
        {onRetry && (
          <button onClick={onRetry} className="tech-button border-red-500/50 text-red-400 hover:bg-red-500">
            Re-Connect
          </button>
        )}
      </div>
    );
  }

  const sortedSegments = [...filteredSegments].sort((a, b) => a.start - b.start);

  return (
    <div className="space-y-6">
      {/* 頂部工具欄 */}
      <div className="flex flex-col sm:flex-row gap-4 items-center bg-white/5 p-4 rounded-xl border border-white/5">
        <div className="relative flex-1 w-full group">
          <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none text-cyan-500/50 group-focus-within:text-cyan-400">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <input
            type="text"
            placeholder="FILTER_BY_KEYWORDS_OR_SPEAKER..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950/50 border border-white/10 rounded-lg py-2 pl-10 pr-4 text-xs font-mono text-white placeholder:text-white/20 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20 transition-all uppercase tracking-tight"
          />
        </div>

        <div className="flex items-center gap-3 px-4 py-2 bg-slate-950/50 rounded-lg border border-white/10">
          <span className="text-[10px] font-mono text-white/40 uppercase tracking-widest">Translation_OS</span>
          <button
            onClick={toggleTranslation}
            className={`relative inline-flex h-5 w-10 items-center rounded-full transition-colors focus:outline-none ${
              showTranslation ? 'bg-cyan-600' : 'bg-white/10'
            }`}
          >
            <span
              className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                showTranslation ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      </div>

      {/* 列表內容 */}
      <div className="space-y-2 overflow-y-auto max-h-[65vh] pr-2 custom-scrollbar">
        {sortedSegments.length > 0 ? (
          sortedSegments.map((segment) => (
            <TranscriptSegmentCard
              key={segment.segment_id}
              segment={segment}
              showTranslation={showTranslation}
            />
          ))
        ) : (
          <div className="text-center py-20 space-y-4">
            <div className="font-mono text-xs text-white/20 uppercase tracking-[0.3em]">Query_Result: Null</div>
            <button 
              onClick={() => setSearchQuery('')}
              className="text-[10px] font-mono text-cyan-400 hover:text-cyan-300 underline underline-offset-4"
            >
              CLEAR_ALL_FILTERS
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
