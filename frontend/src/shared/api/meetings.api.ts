import {MeetingMeta, SummaryData, TranscriptSegment} from '../types';
import {
    StartMeetingProcessRequest,
    StartMeetingProcessResponse,
    SummaryResult,
    TranscriptResult,
    UploadMeetingRequest,
    UploadMeetingResponse,
} from './contracts';
import {getJson, postForm, postJson} from './httpClient';

interface RawTranscriptResult {
    meeting_id: string;
    status: MeetingMeta['status'];
    transcript: Array<TranscriptSegment & { translated_text?: string }>;
}

interface RawSummaryResult {
    meeting_id: string;
    status: MeetingMeta['status'];
    summary?: string;
    key_points?: string[];
    action_items?: Array<{ owner?: string; task: string }>;
}

const normalizeTranscriptSegment = (
    segment: TranscriptSegment & { translated_text?: string },
): TranscriptSegment => {
    return {
        ...segment,
        speaker: segment.speaker || 'UNKNOWN',
        translation: segment.translation ?? segment.translated_text,
    };
};

const normalizeSummary = (result: RawSummaryResult): SummaryData => {
    return {
        summary: result.summary ?? '',
        key_points: result.key_points ?? [],
        action_items: result.action_items ?? [],
    };
};

export const uploadMeeting = async (
    request: UploadMeetingRequest,
    signal?: AbortSignal,
): Promise<UploadMeetingResponse> => {
    const formData = new FormData();
    formData.append('file', request.file);

    if (request.langHint) {
        formData.append('lang_hint', request.langHint);
    }
    if (request.fileName) {
        formData.append('file_name', request.fileName);
    }

    return postForm<UploadMeetingResponse>('/meetings/upload', formData, signal);
};

export const startMeetingProcess = async (
    request: StartMeetingProcessRequest,
    signal?: AbortSignal,
): Promise<StartMeetingProcessResponse> => {
    return postJson<StartMeetingProcessResponse>('/meetings/process', request, signal);
};

export const getMeetingStatus = async (meetingId: string, signal?: AbortSignal): Promise<MeetingMeta> => {
    return getJson<MeetingMeta>(`/meetings/${meetingId}`, signal);
};

export const getMeetingTranscript = async (
    meetingId: string,
    options?: { includeTranslation?: boolean; targetLang?: string; signal?: AbortSignal },
): Promise<TranscriptResult> => {
    const query = new URLSearchParams();
    if (options?.includeTranslation !== undefined) {
        query.set('include_translation', String(options.includeTranslation));
    }
    if (options?.targetLang) {
        query.set('target_lang', options.targetLang);
    }

    const suffix = query.toString() ? `?${query.toString()}` : '';
    const raw = await getJson<RawTranscriptResult>(`/meetings/${meetingId}/transcript${suffix}`, options?.signal);

    return {
        meeting_id: raw.meeting_id,
        status: raw.status,
        transcript: raw.transcript.map(normalizeTranscriptSegment),
    };
};

export const getMeetingSummary = async (meetingId: string, signal?: AbortSignal): Promise<SummaryResult> => {
    const raw = await getJson<RawSummaryResult>(`/meetings/${meetingId}/summary`, signal);

    return {
        meeting_id: raw.meeting_id,
        status: raw.status,
        summary: normalizeSummary(raw),
    };
};


