/**
 * User-data API client. All endpoints require an Auth0 access token via
 * `useUserApi()` (see hooks/useUserApi.ts). The backend extracts user_id from
 * the verified JWT, so the client never sends it explicitly.
 */

export interface ProfileDTO {
    user_id?: string;
    name?: string | null;
    age?: number | null;
    gender?: 'male' | 'female' | 'other' | null;
    isPregnant?: boolean | null;
    pregnancyDueDate?: string | null;
    allergies: string[];
    conditions: string[];
    medications: string[];
    onboarded?: boolean | null;
}

export interface CabinetItemDTO {
    id?: string;
    name: string;
    generic_name?: string | null;
    dosage?: string | null;
    item_type?: string | null;
    quantity: number;
    expiration_date: string;     // YYYY-MM-DD
    added_date?: string;         // YYYY-MM-DD (server-set on create)
    notes?: string | null;
}

export const userPaths = {
    profile: '/user/profile',
    cabinet: '/user/cabinet',
    cabinetItem: (id: string) => `/user/cabinet/${id}`,
} as const;
