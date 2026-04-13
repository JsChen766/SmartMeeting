import {MeetingStatus, SummaryData, TranscriptSegment} from '../types';

export interface ApiErrorPayload {
    code: string;
    message: string;
    details?: Record<string, unknown>;
}

export interface ApiEnvelope<T> {
    success: boolean;
    message: string;
    data: T | null;
    error: ApiErrorPayload | null;
}

export interface UploadMeetingRequest {
    file: File;
    langHint?: string;
    fileName?: string;
}

export interface UploadMeetingResponse {
    meeting_id: string;
    status: MeetingStatus;
    file_name?: string;
}

export interface StartMeetingProcessRequest {
    meeting_id: string;
    target_lang?: string;
    enable_translation?: boolean;
    translation_target_lang?: string;
    enable_summary?: boolean;
}

export interface StartMeetingProcessResponse {
    meeting_id: string;
    status: MeetingStatus;
}

export interface TranscriptResult {
    meeting_id: string;
    status: MeetingStatus;
    transcript: TranscriptSegment[];
}

export interface SummaryResult {
    meeting_id: string;
    status: MeetingStatus;
    summary: SummaryData;
}



