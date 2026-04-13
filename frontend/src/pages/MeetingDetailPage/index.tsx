import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { MeetingStatus, TranscriptSegment, SummaryData, LanguageCode } from '../../shared/types';
import { mapLanguageCodeToName } from '../../shared/utils/language';
import { TranscriptPanel } from '../../widgets/TranscriptPanel';
import { SummaryPanel } from '../../widgets/SummaryPanel';

export interface MeetingDetailPageProps {
  meetingId: string;
  fileName: string;
  status: MeetingStatus;
  targetLanguage?: LanguageCode;
  
  transcriptData?: TranscriptSegment[];
  isTranscriptLoading: boolean;
  isTranscriptError: boolean;
  onRetryTranscript?: () => void;

  summaryData?: SummaryData;
  isSummaryLoading: boolean;
  isSummaryError: boolean;
  onRetrySummary?: () => void;
}

export const MeetingDetailPage: React.FC<MeetingDetailPageProps> = (props) => {
  const {
    meetingId,
    fileName,
    status,
    targetLanguage,
    transcriptData,
    isTranscriptLoading,
    isTranscriptError,
    onRetryTranscript,
    summaryData,
    isSummaryLoading,
    isSummaryError,
    onRetrySummary,
  } = props;

  const [activeTab, setActiveTab] = useState<'transcript' | 'summary'>('transcript');

  const getStatusBadge = (currentStatus: MeetingStatus) => {
    switch (currentStatus) {
      case 'uploaded':
        return (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-400 text-xs font-mono uppercase tracking-wider">
            <span className="h-1.5 w-1.5 rounded-full bg-blue-500 shadow-[0_0_8px_#3b82f6]" />
            Uploaded
          </div>
        );
      case 'processing':
        return (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-xs font-mono uppercase tracking-wider">
            <span className="h-1.5 w-1.5 rounded-full bg-yellow-500 shadow-[0_0_8px_#eab308] animate-pulse" />
            Processing
          </div>
        );
      case 'completed':
        return (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-mono uppercase tracking-wider">
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-500 shadow-[0_0_8px_#06b6d4]" />
            Decrypted
          </div>
        );
      case 'failed':
        return (
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-mono uppercase tracking-wider">
            <span className="h-1.5 w-1.5 rounded-full bg-red-500 shadow-[0_0_8px_#ef4444]" />
            Error
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen p-4 sm:p-8 lg:p-12">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Top Info Bar */}
        <header className="tech-card p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <Link to="/" className="p-2 hover:bg-white/5 rounded-lg transition-colors text-cyan-400">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
                </svg>
              </Link>
              <h1 className="text-2xl font-black tracking-tight uppercase italic neon-glow-cyan truncate max-w-md">
                {fileName || 'Unknown_Source'}
              </h1>
            </div>
            <div className="flex flex-wrap gap-x-6 gap-y-2 pl-10 font-mono text-[10px] text-cyan-400/50 uppercase tracking-widest">
              <span>ID: <span className="text-white/70">{meetingId}</span></span>
              {targetLanguage && (
                <span>Lang: <span className="text-white/70">{mapLanguageCodeToName(targetLanguage)}</span></span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-4 w-full md:w-auto justify-end">
            {getStatusBadge(status)}
          </div>
        </header>

        {/* Main Content Area */}
        <div className="tech-card min-h-[600px] flex flex-col">
          {/* Tabs */}
          <div className="flex border-b border-white/5 bg-white/5" role="tablist">
            <button
              onClick={() => setActiveTab('transcript')}
              className={`flex-1 py-5 font-mono text-xs uppercase tracking-[0.2em] transition-all ${
                activeTab === 'transcript'
                  ? 'bg-cyan-500/10 text-cyan-400 border-b-2 border-cyan-500'
                  : 'text-white/40 hover:text-white/70 hover:bg-white/5'
              }`}
              disabled={status === 'uploaded' || status === 'processing'}
            >
              [ 01_Transcript ]
            </button>
            <button
              onClick={() => setActiveTab('summary')}
              className={`flex-1 py-5 font-mono text-xs uppercase tracking-[0.2em] transition-all ${
                activeTab === 'summary'
                  ? 'bg-cyan-500/10 text-cyan-400 border-b-2 border-cyan-500'
                  : 'text-white/40 hover:text-white/70 hover:bg-white/5'
              }`}
              disabled={status === 'uploaded' || status === 'processing'}
            >
              [ 02_Intelligence ]
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 p-6 sm:p-10 relative">
            {status === 'failed' ? (
              <div className="h-full flex flex-col items-center justify-center text-center space-y-6">
                <div className="w-20 h-20 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center animate-flicker">
                  <svg className="w-10 h-10 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <div className="space-y-2">
                  <h3 className="text-xl font-bold text-red-400 uppercase tracking-tighter">System Malfunction</h3>
                  <p className="text-red-400/60 font-mono text-xs uppercase tracking-widest">Error code: ERR_PROC_FAILED_0X92</p>
                </div>
                <button className="tech-button border-red-500/50 text-red-400 hover:bg-red-500">Re-Initialize</button>
              </div>
            ) : status === 'uploaded' || status === 'processing' ? (
              <div className="h-full flex flex-col items-center justify-center text-center space-y-8">
                <div className="relative">
                  <div className="w-24 h-24 border-4 border-cyan-500/20 rounded-full" />
                  <div className="absolute top-0 left-0 w-24 h-24 border-4 border-cyan-500 border-t-transparent rounded-full animate-spin" />
                  <div className="absolute inset-0 flex items-center justify-center font-mono text-[10px] text-cyan-400 animate-pulse uppercase tracking-tighter">
                    {status === 'uploaded' ? 'Sync' : 'Proc'}
                  </div>
                </div>
                <div className="space-y-2">
                  <h3 className="text-xl font-bold text-white uppercase tracking-tighter italic">Data Stream Decryption</h3>
                  <p className="text-cyan-400/40 font-mono text-xs uppercase tracking-widest animate-flicker">Processing neural networks... Please standby</p>
                </div>
              </div>
            ) : (
              <>
                <div hidden={activeTab !== 'transcript'}>
                  <TranscriptPanel
                    data={transcriptData}
                    isLoading={isTranscriptLoading}
                    isError={isTranscriptError}
                    onRetry={onRetryTranscript}
                  />
                </div>
                <div hidden={activeTab !== 'summary'}>
                  <SummaryPanel
                    data={summaryData}
                    isLoading={isSummaryLoading}
                    isError={isSummaryError}
                    onRetry={onRetrySummary}
                  />
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
