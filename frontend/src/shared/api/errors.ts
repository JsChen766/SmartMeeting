import {ApiErrorPayload} from './contracts';

const FALLBACK_ERROR_CODE = 'UNKNOWN_ERROR';

const ERROR_MESSAGES: Record<string, string> = {
    UNKNOWN_ERROR: 'Unexpected error. Please try again.',
    NETWORK_ERROR: 'Cannot reach server. Please check your network and retry.',
    TIMEOUT_ERROR: 'Request timed out. Please retry.',
    UPLOAD_FILE_MISSING: 'Please select an audio file before uploading.',
    UPLOAD_FILE_TYPE_UNSUPPORTED: 'This file type is not supported.',
    UPLOAD_SAVE_FAILED: 'Unable to save file on server. Please retry.',
    MEETING_NOT_FOUND: 'Meeting not found. Please upload again.',
    MEETING_ALREADY_PROCESSING: 'This meeting is already processing.',
    MEETING_ALREADY_COMPLETED: 'This meeting is already completed.',
    PROCESS_REQUEST_INVALID: 'Invalid process request. Please verify inputs.',
    SUMMARY_NOT_READY: 'Summary is not ready yet. Please refresh later.',
    MEETING_NOT_COMPLETED: 'Meeting is not completed yet.',
};

export class ApiError extends Error {
    code: string;
    details?: Record<string, unknown>;
    status?: number;

    constructor(code: string, message: string, options?: { details?: Record<string, unknown>; status?: number }) {
        super(message);
        this.name = 'ApiError';
        this.code = code;
        this.details = options?.details;
        this.status = options?.status;
    }
}

export const isApiError = (error: unknown): error is ApiError => error instanceof ApiError;

export const toApiError = (
    payload?: Partial<ApiErrorPayload> & { status?: number },
    fallbackMessage?: string,
): ApiError => {
    const code = payload?.code ?? FALLBACK_ERROR_CODE;
    const message = payload?.message ?? fallbackMessage ?? ERROR_MESSAGES[code] ?? ERROR_MESSAGES.UNKNOWN_ERROR;

    return new ApiError(code, message, {
        details: payload?.details,
        status: payload?.status,
    });
};

export const normalizeApiError = (error: unknown): ApiError => {
    if (isApiError(error)) {
        if (error.message) {
            return error;
        }

        return toApiError({code: error.code, details: error.details, status: error.status});
    }

    if (error instanceof DOMException && error.name === 'AbortError') {
        return toApiError({code: 'TIMEOUT_ERROR'});
    }

    if (error instanceof Error && error.message) {
        return toApiError({code: 'NETWORK_ERROR', message: error.message});
    }

    return toApiError();
};

export const getErrorDisplayMessage = (code?: string): string => {
    if (!code) {
        return ERROR_MESSAGES.UNKNOWN_ERROR;
    }

    return ERROR_MESSAGES[code] ?? ERROR_MESSAGES.UNKNOWN_ERROR;
};

