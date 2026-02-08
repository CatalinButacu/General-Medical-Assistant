import type { SearchResponse } from '../types';

/**
 * API Configuration
 * The backend is hosted on a custom server in Zurich.
 */
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "";

export const API_BASE_URL = BACKEND_URL.replace(/\/$/, "");
export const API_SEARCH_URL = API_BASE_URL ? `${API_BASE_URL}/api/v1/search` : "";

/**
 * Check if the backend connection is configured
 */
export function isApiConfigured(): boolean {
    return Boolean(API_BASE_URL);
}

/**
 * Search medicines using the custom RAG model
 */
export async function searchMedicines(query: string): Promise<string> {
    if (!API_SEARCH_URL) {
        throw new Error("Backend API URL is not configured. Please check VITE_BACKEND_URL in your .env file.");
    }

    const response = await fetch(API_SEARCH_URL, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "X-Server-Location": "Zurich"
        },
        body: JSON.stringify({ query }),
    });

    if (!response.ok) {
        throw new Error(`Server Error: ${response.status}`);
    }

    const result = await response.json();

    // Support both Gradio-style {data: [...]} and standard {answer: "..."} formats
    if (result.answer) return result.answer;
    if (result.data && result.data.length > 0) return result.data[0];
    if (result.text) return result.text;

    return "No clear response from the medical database.";
}

/**
 * Health check for the Zurich server
 */
export async function checkHealth(): Promise<boolean> {
    if (!API_BASE_URL) return false;
    try {
        const response = await fetch(`${API_BASE_URL}/health`, {
            method: "GET",
            signal: AbortSignal.timeout(3000),
        });
        return response.ok;
    } catch {
        return false;
    }
}
