/**
 * Shared TypeScript types for RAG Pharma.
 * Centralized from scattered definitions across components.
 */

/**
 * Chat message structure
 */
export interface Message {
    id: string;
    content: string;
    sender: 'user' | 'ai';
    timestamp: Date;
}

/**
 * Medicine data from the API
 */
export interface Medicine {
    name: string;
    genericName?: string;
    dosage?: string;
    type?: string;
    title?: string;
    active_substance?: string;
    category?: string;
    price?: number | string;
    rx?: boolean;
    prescription_required?: boolean;
    url?: string;
    description?: string;
    symptoms?: string[];
    notes?: string;
}

/**
 * API search response structure
 */
export interface SearchResponse {
    data?: string[];
    error?: string;
    query?: string;
    symptom_matches?: Medicine[];
    search_results?: Medicine[];
}

/**
 * Health profile data
 */
export interface HealthProfile {
    id: string;
    name: string;
    age?: number;
    gender?: 'male' | 'female' | 'other';
    isPregnant?: boolean;
    pregnancyDueDate?: string;
    allergies: string[];
    conditions: string[];
    medications: string[];
    notes?: string;
}

/**
 * Medicine cabinet item
 */
export interface CabinetItem extends Medicine {
    id: string;
    quantity: number;
    expirationDate: string;
    addedDate: string;
    isExpired?: boolean;
    daysUntilExpiration?: number;
}
