// Auth via useUserApi(). Backend extracts user_id from the verified JWT.

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

export interface ChatSessionSummary {
    id: string;
    title: string | null;
    message_count: number;
    created_at: string;
    updated_at: string;
}

export interface ChatMessageDTO {
    id: string;
    role: 'user' | 'assistant';
    text: string;
    created_at: string;
}

export interface ChatSessionDetail {
    id: string;
    title: string | null;
    created_at: string;
    updated_at: string;
    messages: ChatMessageDTO[];
}

export const userPaths = {
    profile: '/user/profile',
    cabinet: '/user/cabinet',
    cabinetItem: (id: string) => `/user/cabinet/${id}`,
    chats: '/user/chats',
    chat: (id: string) => `/user/chats/${id}`,
    chatMessages: (id: string) => `/user/chats/${id}/messages`,
} as const;
