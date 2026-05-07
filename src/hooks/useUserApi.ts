import { useAuth0 } from '@auth0/auth0-react';
import { useCallback } from 'react';
import { API_BASE_URL } from '../services/api';

export class ApiError extends Error {
    constructor(public status: number, public body: string, message: string) {
        super(message);
    }
}

export function useUserApi() {
    const { getAccessTokenSilently } = useAuth0();

    return useCallback(
        async <T>(path: string, init: RequestInit = {}): Promise<T> => {
            const token = await getAccessTokenSilently();
            const headers = new Headers(init.headers);
            headers.set('Authorization', `Bearer ${token}`);
            if (init.body && !headers.has('Content-Type')) {
                headers.set('Content-Type', 'application/json');
            }
            const url = API_BASE_URL ? `${API_BASE_URL}${path}` : path;
            const res = await fetch(url, { ...init, headers });
            if (!res.ok) {
                const body = await res.text().catch(() => '');
                throw new ApiError(res.status, body, `HTTP ${res.status}: ${body || res.statusText}`);
            }
            if (res.status === 204) return undefined as T;
            return (await res.json()) as T;
        },
        [getAccessTokenSilently],
    );
}
