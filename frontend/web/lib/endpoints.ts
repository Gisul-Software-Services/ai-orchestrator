import type { ApiEndpointMeta } from "@/types/api";

const API_V1 = "/api/v1";

/**
 * Single registry for playground navigation + future routes.
 * `implemented: false` → placeholder page only (no backend contract yet).
 */
export const API_ENDPOINTS: ApiEndpointMeta[] = [
  // --- Implemented on backend today ---
  {
    id: "generate-topics",
    path: `${API_V1}/generate-topics`,
    method: "POST",
    label: "Topics",
    description: "Generate assessment topics",
    implemented: true,
    section: "generation",
  },
  {
    id: "generate-mcq",
    path: `${API_V1}/generate-mcq`,
    method: "POST",
    label: "MCQ",
    description: "Multiple choice questions",
    implemented: true,
    section: "generation",
  },
  {
    id: "generate-subjective",
    path: `${API_V1}/generate-subjective`,
    method: "POST",
    label: "Subjective",
    description: "Subjective questions",
    implemented: true,
    section: "generation",
  },
  {
    id: "generate-coding",
    path: `${API_V1}/generate-coding`,
    method: "POST",
    label: "Coding",
    description: "Coding problems",
    implemented: true,
    section: "generation",
  },
  {
    id: "generate-sql",
    path: `${API_V1}/generate-sql`,
    method: "POST",
    label: "SQL",
    description: "SQL problems",
    implemented: true,
    section: "generation",
  },
  {
    id: "generate-aiml",
    path: `${API_V1}/generate-aiml`,
    method: "POST",
    label: "AIML (synthetic)",
    description: "AIML dataset generation",
    implemented: true,
    section: "generation",
  },
  {
    id: "generate-aiml-library",
    path: `${API_V1}/generate-aiml-library`,
    method: "POST",
    label: "AIML Library",
    description: "AIML from catalog / FAISS",
    implemented: true,
    section: "generation",
  },
  {
    id: "enrich-dsa",
    path: `${API_V1}/enrich-dsa`,
    method: "POST",
    label: "Enrich DSA",
    description: "DSA enrichment pipeline",
    implemented: true,
    section: "dsa",
  },
  {
    id: "generate-dsa-question",
    path: `${API_V1}/generate-dsa-question`,
    method: "POST",
    label: "DSA Question",
    description: "Generate DSA question",
    implemented: true,
    section: "dsa",
  },

  // --- Reserved for later (UI shell only) ---
  {
    id: "evaluate",
    path: `${API_V1}/evaluate`,
    method: "POST",
    label: "Evaluate",
    description: "Evaluation engine (planned)",
    implemented: false,
    section: "future",
  },
  {
    id: "generate-data-engineering",
    path: `${API_V1}/generate-data-engineering`,
    method: "POST",
    label: "Data Engineering",
    description: "Data engineering generation (planned)",
    implemented: false,
    section: "future",
  },
  {
    id: "generate-devops",
    path: `${API_V1}/generate-devops`,
    method: "POST",
    label: "DevOps",
    description: "DevOps generation (planned)",
    implemented: false,
    section: "future",
  },
  {
    id: "generate-system-design",
    path: `${API_V1}/generate-system-design`,
    method: "POST",
    label: "System Design",
    description: "System design generation (planned)",
    implemented: false,
    section: "future",
  },
  /** Dedicated “raw” DSA enrichment UI — backend path TBD (may reuse enrich-dsa). */
  {
    id: "enrich-dsa-raw",
    path: `${API_V1}/enrich-dsa-raw`,
    method: "POST",
    label: "Enrich DSA (raw)",
    description: "Raw DSA enrichment payload (planned)",
    implemented: false,
    section: "future",
  },
];

export function getEndpointById(id: string): ApiEndpointMeta | undefined {
  return API_ENDPOINTS.find((e) => e.id === id);
}
