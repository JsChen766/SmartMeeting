import {BrowserRouter as Router, Route, Routes, useParams, useSearchParams} from 'react-router-dom';
import {useMeetingSummaryQuery, useMeetingTranscriptQuery} from './features/meeting-results';
import {useMeetingStatusPolling} from './features/poll-meeting-status';
import {UploadPage} from './pages/UploadPage';
import {MeetingDetailPage} from './pages/MeetingDetailPage';
import {normalizeApiError} from './shared/api';
import {LanguageCode, MeetingStatus} from './shared/types';
import {ErrorBanner} from './widgets/ErrorBanner';
import {ProcessingStatusPanel} from './widgets/ProcessingStatusPanel';

function MeetingDetailWrapper() {
    const {meetingId} = useParams<{ meetingId: string }>();
    const [searchParams] = useSearchParams();
    const fileNameFromQuery = searchParams.get('fileName') || '未命名會議';
    const targetLang = (searchParams.get('targetLang') as LanguageCode) || 'man';
    const safeMeetingId = meetingId || 'unknown';

    const statusPollingQuery = useMeetingStatusPolling(meetingId, {
        enabled: Boolean(meetingId),
    });

    const resolvedStatus: MeetingStatus = statusPollingQuery.data?.status ?? 'processing';
    const shouldFetchResults = resolvedStatus === 'completed';

    const transcriptQuery = useMeetingTranscriptQuery(meetingId, {
        enabled: Boolean(meetingId) && shouldFetchResults,
        includeTranslation: true,
        targetLang,
    });

    const summaryQuery = useMeetingSummaryQuery(meetingId, {
        enabled: Boolean(meetingId) && shouldFetchResults,
    });

    const fileName = statusPollingQuery.data?.file_name || fileNameFromQuery;

    const statusError = statusPollingQuery.error ? normalizeApiError(statusPollingQuery.error) : null;

    return (
        <div className="space-y-3">
            {statusError ? <ErrorBanner message={`ERROR [${statusError.code}]: ${statusError.message}`}/> : null}
            <div className="px-4 sm:px-8 lg:px-12">
                <ProcessingStatusPanel status={resolvedStatus} timedOut={statusPollingQuery.isTimedOut}/>
            </div>
            <MeetingDetailPage
                meetingId={safeMeetingId}
                fileName={fileName}
                status={resolvedStatus}
                targetLanguage={targetLang}
                transcriptData={transcriptQuery.data?.transcript}
                isTranscriptLoading={shouldFetchResults ? transcriptQuery.isLoading : false}
                isTranscriptError={shouldFetchResults ? transcriptQuery.isError : false}
                onRetryTranscript={transcriptQuery.refetch}
                summaryData={summaryQuery.data?.summary}
                isSummaryLoading={shouldFetchResults ? summaryQuery.isLoading : false}
                isSummaryError={shouldFetchResults ? summaryQuery.isError : false}
                onRetrySummary={summaryQuery.refetch}
            />
        </div>
    );
}

function App() {
    return (
        <div className="app-bg min-h-screen">
            <div className="app-bg__grid" aria-hidden="true"/>
            <div className="app-bg__blob app-bg__blob--1" aria-hidden="true"/>
            <div className="app-bg__blob app-bg__blob--2" aria-hidden="true"/>
            <div className="app-bg__blob app-bg__blob--3" aria-hidden="true"/>
            <div className="relative z-10">
                <Router>
                    <Routes>
                        <Route path="/" element={<UploadPage/>}/>
                        <Route path="/meetings/:meetingId" element={<MeetingDetailWrapper/>}/>
                        <Route
                            path="*"
                            element={
                                <div className="min-h-screen flex items-center justify-center p-6">
                                    <div
                                        className="glass rounded-2xl border border-white/40 shadow-xl p-10 text-center max-w-md w-full">
                                        <div
                                            className="mx-auto mb-4 h-12 w-12 rounded-2xl bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 shadow-lg"/>
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
