import { BrowserRouter as Router, Routes, Route, useParams, useSearchParams } from 'react-router-dom';
import { UploadPage } from './pages/UploadPage';
import { MeetingDetailPage } from './pages/MeetingDetailPage';
import { MeetingStatus, TranscriptSegment, SummaryData, LanguageCode } from './shared/types';

const mockTranscript: TranscriptSegment[] = [
  {
    segment_id: '1',
    start: 0,
    end: 5,
    speaker: 'Speaker 1',
    text: 'Hello everyone, welcome to the meeting.',
    lang: 'eng',
    translation: '大家好，歡迎參加會議。',
  },
  {
    segment_id: '2',
    start: 6,
    end: 10,
    speaker: 'Speaker 2',
    text: 'Thank you for joining us today.',
    lang: 'eng',
    translation: '感謝大家今天加入我們。',
  },
  {
    segment_id: '3',
    start: 11,
    end: 15,
    speaker: 'Speaker 1',
    text: 'We have a lot to discuss.',
    lang: 'eng',
    translation: '我們有很多事情要討論。',
  },
];

const mockSummary: SummaryData = {
  summary: '本次會議主要討論了專案進度、市場策略和下一步行動。',
  key_points: [
    '專案進度符合預期',
    '市場策略需要進一步細化',
    '下週將召開專題會議討論具體實施方案',
  ],
  action_items: [
    { owner: 'Alice', task: '完成市場分析報告' },
    { owner: 'Bob', task: '準備下週會議的議程' },
    { task: '發送會議紀要' },
  ],
};

function MeetingDetailWrapper() {
  const { meetingId } = useParams<{ meetingId: string }>();
  const [searchParams] = useSearchParams();
  const fileName = searchParams.get('fileName') || '未命名會議';
  const targetLang = searchParams.get('targetLang') as LanguageCode || 'man';

  // 這裡的 mock 數據將被 API 呼叫取代
  const status: MeetingStatus = 'completed'; // 實際應從 API 獲取

  return (
    <MeetingDetailPage
      meetingId={meetingId || 'unknown'}
      fileName={fileName}
      status={status}
      targetLanguage={targetLang}
      transcriptData={mockTranscript}
      isTranscriptLoading={false}
      isTranscriptError={false}
      summaryData={mockSummary}
      isSummaryLoading={false}
      isSummaryError={false}
    />
  );
}

function App() {
  return (
    <div className="app-bg min-h-screen">
      <div className="app-bg__grid" aria-hidden="true" />
      <div className="app-bg__blob app-bg__blob--1" aria-hidden="true" />
      <div className="app-bg__blob app-bg__blob--2" aria-hidden="true" />
      <div className="app-bg__blob app-bg__blob--3" aria-hidden="true" />
      <div className="relative z-10">
        <Router>
          <Routes>
            <Route path="/" element={<UploadPage />} />
            <Route path="/meetings/:meetingId" element={<MeetingDetailWrapper />} />
            <Route
              path="*"
              element={
                <div className="min-h-screen flex items-center justify-center p-6">
                  <div className="glass rounded-2xl border border-white/40 shadow-xl p-10 text-center max-w-md w-full">
                    <div className="mx-auto mb-4 h-12 w-12 rounded-2xl bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 shadow-lg" />
                    <div className="text-2xl font-extrabold text-gray-900">404</div>
                    <div className="text-sm text-gray-700 mt-2">页面不存在</div>
                    <a
                      href="/"
                      className="mt-6 inline-flex items-center justify-center px-6 py-3 rounded-xl bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 text-white font-semibold shadow-lg hover:brightness-110 active:brightness-95 transition-all"
                    >
                      返回首页
                    </a>
                  </div>
                </div>
              }
            />
          </Routes>
        </Router>
      </div>
    </div>
  );
}

export default App;
