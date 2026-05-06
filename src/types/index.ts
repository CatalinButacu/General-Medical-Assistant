/**
 * Shared TypeScript types for Med Assist.
 * Backend DTOs mirror med_assist/api/main.py Pydantic models.
 */

/**
 * Chat message structure (UI-only). Assistant messages are populated
 * incrementally from the /chat SSE stream:
 *   - `triage`     arrives first (label, red_flags, recommended_action)
 *   - `medicines`  arrives next (skipped on EMERGENCY)
 *   - `text`       grows token-by-token from `token` events
 *   - `isStreaming` flips false on `done`
 */
export interface Message {
    id: string;
    sender: 'user' | 'ai';
    timestamp: Date;
    text?: string;
    triage?: TriageEvent;
    medicines?: MedicineDTO[];
    isStreaming?: boolean;
    error?: string;
}

/**
 * Triage payload emitted by the backend SSE stream.
 */
export interface TriageEvent {
    label: TriageLabel;
    rationale: string;
    recommended_action_ro: string;
    confidence: number;
    red_flags: RedFlagDTO[];
}

/**
 * Triage label produced by the backend. FOLLOWUP is emitted during the
 * mandatory information-gathering phase (first 2 user turns), when the
 * assistant must ask a clarifying question and not recommend yet.
 */
export type TriageLabel = 'EMERGENCY' | 'OTC_SAFE' | 'UNCERTAIN' | 'FOLLOWUP';

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
 * Result of POST /scan — Gemini Vision OCR + ANMDM corpus match.
 */
export interface ScanExtraction {
    trade_name: string | null;
    expiration_date: string | null;   // YYYY-MM-DD
    dosage: string | null;
    form: string | null;
    confidence: number;
}

export interface ScanMedicineMatch {
    trade_name: string;
    dci: string;
    form: string;
    concentration: string;
    atc_code: string;
    rx_status: 'OTC' | 'RX' | 'RESTRICTED' | 'MIXED' | 'UNKNOWN';
    category: string;
    lay_symptoms: string[];
    rcp_url: string;
    prospect_url: string;
    match_score: number;
}

export interface ScanResponse {
    extracted: ScanExtraction;
    matched: ScanMedicineMatch | null;
    candidates: ScanMedicineMatch[];
    latency_ms: number;
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
    onboarded?: boolean;
}

export interface CabinetItem extends Medicine {
    id: string;
    quantity: number;
    expirationDate: string;
    addedDate: string;
    isExpired?: boolean;
    daysUntilExpiration?: number;
}
