import type { SearchResponse } from '../types';

const rawBaseUrl = import.meta.env.VITE_HF_API_URL || "";

function getBaseUrl(): string {
    if (!rawBaseUrl) return "";
    if (rawBaseUrl.includes(".hf.space")) {
        return rawBaseUrl.split(".hf.space")[0] + ".hf.space";
    }
    return rawBaseUrl.replace(/\/$/, "");
}

export const HF_API_BASE_URL = getBaseUrl();
export const HF_API_PREDICT_URL = HF_API_BASE_URL ? `${HF_API_BASE_URL}/api/v1/search` : "";
export const HF_SPACE_URL = "https://huggingface.co/spaces/catalinbutacu/rag-pharma-assistant";

export function isApiConfigured(): boolean {
    return Boolean(HF_API_PREDICT_URL);
}

export async function searchMedicines(query: string): Promise<string> {
    if (!HF_API_PREDICT_URL) {
        throw new Error("API URL is not configured. Please check VITE_HF_API_URL.");
    }

    const response = await fetch(HF_API_PREDICT_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ data: [query] }),
    });

    if (!response.ok) {
        throw new Error(`Backend Error: ${response.status}`);
    }

    const result: SearchResponse = await response.json();
    if (result.data && result.data.length > 0) {
        return result.data[0];
    }

    throw new Error("Invalid response format from backend.");
}

export async function checkHealth(): Promise<boolean> {
    if (!HF_API_BASE_URL) return false;
    try {
        const response = await fetch(`${HF_API_BASE_URL}/health`, {
            method: "GET",
            signal: AbortSignal.timeout(5000),
        });
        return response.ok;
    } catch {
        return false;
    }
}
