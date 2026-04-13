import {ApiEnvelope} from './contracts';
import {toApiError} from './errors';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const joinUrl = (path: string): string => {
    const normalizedPath = path.startsWith('/') ? path : `/${path}`;
    return `${API_BASE_URL}${normalizedPath}`;
};

const parseJsonResponse = async <T>(response: Response): Promise<T | null> => {
    const text = await response.text();
    if (!text) {
        return null;
    }

    try {
        return JSON.parse(text) as T;
    } catch {
        throw toApiError({code: 'INVALID_JSON_RESPONSE', status: response.status});
    }
};

const validateEnvelope = <T>(payload: unknown): ApiEnvelope<T> => {
    if (!payload || typeof payload !== 'object') {
        throw toApiError({code: 'INVALID_API_ENVELOPE'});
    }

    const record = payload as Record<string, unknown>;
    if (typeof record.success !== 'boolean' || typeof record.message !== 'string') {
        throw toApiError({code: 'INVALID_API_ENVELOPE'});
    }

    return payload as ApiEnvelope<T>;
};

const request = async <T>(path: string, init?: RequestInit): Promise<T> => {
    let response: Response;
    try {
        response = await fetch(joinUrl(path), init);
    } catch {
        throw toApiError({code: 'NETWORK_ERROR'});
    }

    const payload = await parseJsonResponse<ApiEnvelope<T>>(response);
    const envelope = validateEnvelope<T>(payload);

    if (!response.ok || !envelope.success) {
        throw toApiError({
            code: envelope.error?.code ?? `HTTP_${response.status}`,
            message: envelope.error?.message ?? envelope.message,
            details: envelope.error?.details,
            status: response.status,
        });
    }

    if (envelope.data === null) {
        throw toApiError({code: 'EMPTY_RESPONSE_DATA', status: response.status});
    }

    return envelope.data;
};

export const getJson = <T>(path: string, signal?: AbortSignal): Promise<T> => {
    return request<T>(path, {
        method: 'GET',
        headers: {
            Accept: 'application/json',
        },
        signal,
    });
};

export const postJson = <T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> => {
    return request<T>(path, {
        method: 'POST',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        signal,
    });
};

export const postForm = <T>(path: string, formData: FormData, signal?: AbortSignal): Promise<T> => {
    return request<T>(path, {
        method: 'POST',
        headers: {
            Accept: 'application/json',
        },
        body: formData,
        signal,
    });
};


