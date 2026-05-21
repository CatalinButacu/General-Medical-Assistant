/**
 * Shared TypeScript types for Med Assist.
 * Backend DTOs mirror med_assist/api/main.py Pydantic models.
 */

/**
 * Chat message structure (UI-only). Assistant messages are populated
 * incrementally from the /chat SSE stream:
 *   - `intent`     arrives first on non-emergency turns (routing decision)
 *   - `triage`     arrives next on symptom-triage turns (skipped on explain branch)
 *   - `medicines`  arrives next (skipped on EMERGENCY)
 *   - `text`       grows token-by-token from `token` events
 *   - `isStreaming` flips false on `done`
 */
export interface Message {
    id: string;
    sender: 'user' | 'ai';
    timestamp: Date;
    text?: string;
    intent?: IntentEvent;
    triage?: TriageEvent;
    medicines?: MedicineDTO[];
    isStreaming?: boolean;
    error?: string;
    /**
     * UI-only — derived as each SSE event arrives. Lets the bubble surface
     * 'scanning red flags → searching → drafting' breadcrumbs before the
     * first token lands. Reset to 'done' on the `done` event.
     */
    streamPhase?: 'scanning' | 'classifying' | 'searching' | 'drafting' | 'done';
}

/**
 * Intent classifier output — tells the UI which conversational branch
 * the backend picked for this turn. `MEDICINE_LOOKUP` means the explain
 * flow runs (no symptom questions); `SYMPTOM_TRIAGE` is the default
 * followup-or-recommend loop.
 */
export interface IntentEvent {
    label: 'SYMPTOM_TRIAGE' | 'MEDICINE_LOOKUP';
    confidence: number;
    matched_terms: string[];
    rationale: string;
    medicine_trade_name: string | null;
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
    all_text?: string;                // Full OCR dump, used as fallback search query
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
 * Router-state payload from CameraScanner → MedicineCabinet (`/cabinet`).
 * What the cabinet add-form needs to pre-fill itself after an OCR scan.
 * NOT the on-server DTO — see CabinetItemDTO in services/userApi.ts for that.
 */
export interface CabinetAddState {
    name: string;
    genericName?: string;
    dosage?: string;
    type?: string;
    category?: string;
    prescription_required?: boolean;
    rx?: boolean;
    symptoms?: string[];
    url?: string;
    expirationDate?: string;
}

/**
 * Router-state payload from CameraScanner → HealthProfile (`/profile`).
 * The HealthProfile page reads this to display a safety-check banner; it
 * only needs the identifying fields, not the full DTO.
 */
export interface MedicineSafetyTarget {
    name: string;
    dosage?: string;
    type?: string;
}
