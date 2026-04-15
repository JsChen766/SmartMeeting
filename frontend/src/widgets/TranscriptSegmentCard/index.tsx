import React from 'react';
import { TranscriptSegment } from '../../shared/types';
import { formatTimeRange } from '../../shared/utils/timeFormat';

export interface TranscriptSegmentCardProps {
  segment: TranscriptSegment;
  showTranslation: boolean;
}

export const TranscriptSegmentCard: React.FC<TranscriptSegmentCardProps> = ({ segment, showTranslation }) => {
  const speakerName = segment.speaker || 'UNKNOWN_IDENTITY';
  
  return (
    <div className="group relative bg-white/5 border-l-2 border-cyan-500/30 hover:border-cyan-500 hover:bg-white/10 transition-all duration-300 p-5 rounded-r-xl mb-4 overflow-hidden">
      {/* 背景裝飾 */}
      <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-20 transition-opacity">
        <span className="font-mono text-[40px] font-black tracking-tighter">0{segment.segment_id}</span>
      </div>

      <div className="relative z-10 space-y-3">
        <div className="flex justify-between items-center">
          <span className="text-[10px] font-mono font-bold px-2 py-0.5 bg-cyan-500/20 text-cyan-400 rounded uppercase tracking-widest border border-cyan-500/20">
            {speakerName}
          </span>
          <span className="text-[10px] font-mono text-white/40 tracking-widest">
            T_STAMP: [{formatTimeRange(segment.start, segment.end)}]
          </span>
        </div>

        <div className="text-white/90 leading-relaxed tracking-wide text-sm font-medium">
          {segment.text}
        </div>

        {showTranslation && (
          <div className="mt-4 pt-4 border-t border-white/5">
            <div className="text-[10px] font-mono text-magenta-400/60 uppercase tracking-widest mb-2" style={{ color: 'rgba(255, 0, 255, 0.6)' }}>
              // Translation_Layer
            </div>
            {segment.translation ? (
              <p className="text-white/70 italic text-sm border-l border-magenta-500/30 pl-3" style={{ borderLeftColor: 'rgba(255, 0, 255, 0.3)' }}>
                {segment.translation}
              </p>
            ) : (
              <p className="text-white/30 italic text-xs font-mono">NO_DATA_AVAILABLE</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
