export type MeetingStatus = 'uploaded' | 'processing' | 'completed' | 'failed';

export type LanguageCode = 'man' | 'can' | 'eng';

export interface ErrorInfo {
    code: string;
    message: string;
    details?: Record<string, unknown>;
}

export interface MeetingMeta {
    meeting_id: string;
    status: MeetingStatus;
    file_name?: string;
    created_at?: string;
    updated_at?: string;
    available_results?: {
        transcript?: boolean;
        translation?: boolean;
        summary?: boolean;
    };
}

export interface TranscriptSegment {
    segment_id: string;
    start: number;
    end: number;
    speaker: string;
    text: string;
    lang: string;
    translation?: string;
    source_lang?: string;
    target_lang?: string;
    confidence?: number;
}

export interface SummaryData {
    summary: string;
    key_points: string[];
    action_items: ActionItem[];
}

export interface ActionItem {
    owner?: string;
    task: string;
}
