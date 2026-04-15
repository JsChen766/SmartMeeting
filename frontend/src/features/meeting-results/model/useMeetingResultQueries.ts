import {useQuery} from '@tanstack/react-query';
import {getMeetingSummary, getMeetingTranscript} from '../../../shared/api';

export const useMeetingTranscriptQuery = (
    meetingId?: string,
    options?: { enabled?: boolean; includeTranslation?: boolean; targetLang?: string },
) => {
    return useQuery({
        queryKey: ['meeting-transcript', meetingId, options?.includeTranslation ?? true, options?.targetLang],
        queryFn: ({signal}) =>
            getMeetingTranscript(meetingId as string, {
                includeTranslation: options?.includeTranslation ?? true,
                targetLang: options?.targetLang,
                signal,
            }),
        enabled: Boolean(meetingId) && (options?.enabled ?? true),
        retry: 1,
    });
};

export const useMeetingSummaryQuery = (meetingId?: string, options?: { enabled?: boolean }) => {
    return useQuery({
        queryKey: ['meeting-summary', meetingId],
        queryFn: ({signal}) => getMeetingSummary(meetingId as string, signal),
        enabled: Boolean(meetingId) && (options?.enabled ?? true),
        retry: 1,
    });
};

