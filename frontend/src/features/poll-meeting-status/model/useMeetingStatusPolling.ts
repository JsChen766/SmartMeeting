import {useQuery} from '@tanstack/react-query';
import {useEffect, useMemo, useState} from 'react';
import {getMeetingStatus} from '../../../shared/api';
import {MeetingMeta} from '../../../shared/types';

export interface MeetingPollingOptions {
    enabled?: boolean;
    intervalMs?: number;
    timeoutMs?: number;
}

const DEFAULT_INTERVAL_MS = Number(import.meta.env.VITE_POLL_INTERVAL_MS ?? 3000);
const DEFAULT_TIMEOUT_MS = Number(import.meta.env.VITE_POLL_TIMEOUT_MS ?? 600000);

const isTerminalStatus = (status?: MeetingMeta['status']): boolean => {
    return status === 'completed' || status === 'failed';
};

export const useMeetingStatusQuery = (
    meetingId?: string,
    options?: { enabled?: boolean },
) => {
    return useQuery({
        queryKey: ['meeting-status', meetingId],
        queryFn: ({signal}) => getMeetingStatus(meetingId as string, signal),
        enabled: Boolean(meetingId) && (options?.enabled ?? true),
    });
};

export const useMeetingStatusPolling = (meetingId?: string, options?: MeetingPollingOptions) => {
    const enabled = Boolean(meetingId) && (options?.enabled ?? true);
    const intervalMs = options?.intervalMs ?? DEFAULT_INTERVAL_MS;
    const timeoutMs = options?.timeoutMs ?? DEFAULT_TIMEOUT_MS;

    const [isTimedOut, setIsTimedOut] = useState(false);

    useEffect(() => {
        if (!enabled) {
            setIsTimedOut(false);
            return;
        }

        setIsTimedOut(false);
    }, [meetingId, enabled]);

    const query = useQuery({
        queryKey: ['meeting-status-polling', meetingId],
        queryFn: ({signal}) => getMeetingStatus(meetingId as string, signal),
        enabled,
        refetchInterval: (queryState) => {
            if (isTimedOut) {
                return false;
            }

            const status = (queryState.state.data as MeetingMeta | undefined)?.status;
            if (isTerminalStatus(status)) {
                return false;
            }

            return intervalMs;
        },
        retry: 1,
    });

    useEffect(() => {
        if (!enabled || isTimedOut) {
            return;
        }

        if (isTerminalStatus(query.data?.status)) {
            return;
        }

        const timeoutId = window.setTimeout(() => {
            setIsTimedOut(true);
        }, timeoutMs);

        return () => {
            window.clearTimeout(timeoutId);
        };
    }, [enabled, isTimedOut, timeoutMs, query.data?.status]);

    const canPoll = useMemo(() => {
        return enabled && !isTimedOut && !isTerminalStatus(query.data?.status);
    }, [enabled, isTimedOut, query.data?.status]);

    return {
        ...query,
        isTimedOut,
        canPoll,
    };
};



