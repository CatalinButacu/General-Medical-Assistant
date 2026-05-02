/**
 * Shared TypeScript types for Med Assist.
 * Backend DTOs mirror med_assist/api/main.py Pydantic models.
 */

/**
 * Chat message structure (UI-only).
 */
export interface Message {
    id: string;
    sender: 'user' | 'ai';
    timestamp: Date;
    /** Free text used for the user's outgoing message and welcome bubble. */
    text?: string;
    /** Structured AI response from /advise. When set, render the rich card. */
    advise?: AdviseResponse;
}

/**
 * Triage label produced by the backend.
 */
export type TriageLabel = 'EMERGENCY' | 'OTC_SAFE' | 'UNCERTAIN';

/**
 * One red-flag rule that fired for an emergency-classified query.
 */
export interface RedFlagDTO {
    name: string;
    category: string;
    description: string;
    severity: 'emergency' | 'urgent' | 'see_doctor';
    matched_pattern: string;
}

/**
 * One medicine surfaced by retrieval.
 */
export interface MedicineDTO {
    trade_name: string;
    dci: string;
    form: string;
    concentration: string;
    atc_code: string;
    rx_status: 'OTC' | 'RX' | 'RESTRICTED' | 'MIXED' | 'UNKNOWN';
    category: string;
    lay_symptoms: string[];
    score: number;
    best_chunk_type: string;
    best_chunk_snippet: string;
    rcp_url: string;
    prospect_url: string;
}

/**
 * Full structured advice response from POST /advise.
 */
export interface AdviseResponse {
    label: TriageLabel;
    rationale: string;
    recommended_action_ro: string;
    confidence: number;
    red_flags: RedFlagDTO[];
    medicines: MedicineDTO[];
    latency_ms: number;
}

/**
 * Request body for POST /advise.
 */
export interface AdviseRequest {
    query: string;
    otc_only?: boolean;
    top_k?: number;
}

/**
 * Index manifest from GET /manifest.
 */
export interface ManifestResponse {
    model: string;
    embedding_dim: number;
    medicine_count: number;
    chunk_count: number;
    encode_seconds: number;
    built_at: string;
}

/**
 * Legacy: kept for components that haven't migrated to MedicineDTO yet
 * (MedicineCabinet, HealthProfile, CameraScanner). Do not use for new code.
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

export interface CabinetItem extends Medicine {
    id: string;
    quantity: number;
    expirationDate: string;
    addedDate: string;
    isExpired?: boolean;
    daysUntilExpiration?: number;
}
