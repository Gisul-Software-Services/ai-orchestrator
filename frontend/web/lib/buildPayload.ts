/**
 * Request bodies for POST /api/v1/* — mirrors the API payload builders on the backend.
 */

export type EndpointId =
  | "generate-topics"
  | "generate-mcq"
  | "generate-subjective"
  | "generate-coding"
  | "generate-sql"
  | "generate-aiml"
  | "generate-aiml-library"
  | "generate-dsa-question"
  | "enrich-dsa";

export interface PlaygroundFormState {
  useCache: boolean;
  numQuestions: number;
  // topics
  assessmentTitle: string;
  jobDesignation: string;
  skills: string;
  experienceMin: number;
  experienceMax: number;
  experienceMode: string;
  // shared topic-style
  topic: string;
  difficulty: string;
  targetAudience: string;
  language: string;
  databaseType: string;
  jobRole: string;
  experienceYears: string;
  concepts: string;
  dsaLanguages: string[];
  // enrich-dsa raw JSON
  enrichDsaJson: string;
  /** Sent as `org_id` on every POST JSON body when non-empty. */
  orgId: string;
}

export const EXPERIENCE_YEAR_OPTIONS = [
  "0-1 (Fresher)",
  "1-3 (Junior)",
  "3-5 (Mid-level)",
  "5-8 (Senior)",
  "8+ (Staff/Principal)",
] as const;

export const DSA_LANGUAGE_OPTIONS = [
  "python",
  "java",
  "javascript",
  "typescript",
  "kotlin",
  "go",
  "rust",
  "cpp",
  "csharp",
  "c",
] as const;

export const DEFAULT_FORM: PlaygroundFormState = {
  useCache: true,
  numQuestions: 3,
  assessmentTitle: "Python Developer Assessment",
  jobDesignation: "Software Developer",
  skills: "Python, FastAPI, SQL",
  experienceMin: 1,
  experienceMax: 3,
  experienceMode: "corporate",
  topic: "Python list slicing",
  difficulty: "Easy",
  targetAudience: "Mid-level Software Developers",
  language: "Python",
  databaseType: "PostgreSQL",
  jobRole: "Software Engineer",
  experienceYears: "3-5 (Mid-level)",
  concepts: "classification, imbalanced data",
  dsaLanguages: ["python", "java", "javascript"],
  enrichDsaJson: `{
  "title": "Two Sum",
  "task_id": "two-sum",
  "input_output": []
}`,
  orgId: process.env.NEXT_PUBLIC_PLAYGROUND_ORG_ID ?? "",
};

/** Resolved org for API: form field, else `NEXT_PUBLIC_PLAYGROUND_ORG_ID` (must match `organization_db`). */
export function effectivePlaygroundOrgId(f: PlaygroundFormState): string {
  return f.orgId.trim() || process.env.NEXT_PUBLIC_PLAYGROUND_ORG_ID?.trim() || "";
}

/** Adds `org_id` to the JSON body when resolved org is non-empty (backend expects snake_case). */
export function mergeOrgIdIntoBody(
  f: PlaygroundFormState,
  body: Record<string, unknown>
): Record<string, unknown> {
  const id = effectivePlaygroundOrgId(f);
  if (!id) return body;
  return { ...body, org_id: id };
}

export function buildPayload(
  endpoint: EndpointId,
  f: PlaygroundFormState
): Record<string, unknown> {
  const nq = Math.max(1, Math.min(20, Math.floor(f.numQuestions)));
  const base: Record<string, unknown> = {
    num_questions: nq,
    use_cache: f.useCache,
  };

  let out: Record<string, unknown>;
  switch (endpoint) {
    case "generate-topics":
      out = {
        ...base,
        assessment_title: f.assessmentTitle,
        job_designation: f.jobDesignation,
        skills: f.skills.split(",").map((s) => s.trim()).filter(Boolean),
        experience_min: f.experienceMin,
        experience_max: f.experienceMax,
        experience_mode: f.experienceMode,
        num_topics: nq,
      };
      break;
    case "generate-mcq":
      out = {
        ...base,
        topic: f.topic,
        difficulty: f.difficulty,
        target_audience: f.targetAudience,
      };
      break;
    case "generate-subjective":
      out = {
        ...base,
        topic: f.topic,
        difficulty: f.difficulty,
        target_audience: f.targetAudience,
      };
      break;
    case "generate-coding":
      out = {
        ...base,
        topic: f.topic,
        difficulty: f.difficulty,
        language: f.language,
        job_role: f.jobRole,
        experience_years: f.experienceYears,
      };
      break;
    case "generate-sql":
      out = {
        ...base,
        topic: f.topic,
        difficulty: f.difficulty,
        database_type: f.databaseType,
        job_role: f.jobRole,
        experience_years: f.experienceYears,
      };
      break;
    case "generate-aiml":
      out = {
        use_cache: f.useCache,
        topic: f.topic,
        difficulty: f.difficulty,
      };
      break;
    case "generate-aiml-library": {
      const concepts = f.concepts
        .split(",")
        .map((c) => c.trim())
        .filter(Boolean);
      out = {
        use_cache: f.useCache,
        topic: f.topic,
        difficulty: f.difficulty,
        concepts,
      };
      break;
    }
    case "generate-dsa-question": {
      const concepts = f.concepts
        .split(",")
        .map((c) => c.trim())
        .filter(Boolean);
      out = {
        topic: f.topic,
        difficulty: f.difficulty,
        concepts,
        languages: f.dsaLanguages,
      };
      break;
    }
    case "enrich-dsa":
      throw new Error("enrich-dsa uses parseEnrichDsaBody(), not buildPayload()");
    default: {
      const _exhaustive: never = endpoint;
      throw new Error(`Unhandled: ${_exhaustive}`);
    }
  }
  return mergeOrgIdIntoBody(f, out);
}

export function parseEnrichDsaBody(json: string): Record<string, unknown> {
  const parsed = JSON.parse(json) as unknown;
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Enrich DSA body must be a JSON object");
  }
  return parsed as Record<string, unknown>;
}
