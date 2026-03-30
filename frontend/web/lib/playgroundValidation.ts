import {
  effectivePlaygroundOrgId,
  type EndpointId,
  type PlaygroundFormState,
} from "./buildPayload";

/**
 * Client-side checks before POST. Returns user-facing error lines (empty = OK).
 */
export function validatePlaygroundForm(
  endpoint: EndpointId,
  form: PlaygroundFormState
): string[] {
  const errs: string[] = [];

  if (!effectivePlaygroundOrgId(form)) {
    errs.push(
      "Organization ID is required: set Org ID in the form or NEXT_PUBLIC_PLAYGROUND_ORG_ID (must match organization_db)."
    );
  }

  const nq = Math.floor(Number(form.numQuestions));
  if (!Number.isFinite(nq) || nq < 1 || nq > 20) {
    errs.push("Number of questions must be between 1 and 20.");
  }

  const needsTopic = [
    "generate-mcq",
    "generate-subjective",
    "generate-coding",
    "generate-sql",
    "generate-aiml",
    "generate-aiml-library",
    "generate-dsa-question",
  ].includes(endpoint);

  if (needsTopic && !form.topic.trim()) {
    errs.push("Topic is required for this endpoint.");
  }

  if (endpoint === "generate-topics") {
    if (!form.assessmentTitle.trim()) {
      errs.push("Assessment title is required.");
    }
    if (!form.skills.trim()) {
      errs.push("Enter at least one skill (comma separated).");
    }
    if (form.experienceMin > form.experienceMax) {
      errs.push("Min experience cannot be greater than max experience.");
    }
  }

  if (["generate-mcq", "generate-subjective"].includes(endpoint)) {
    if (!form.targetAudience.trim()) {
      errs.push("Target audience is required.");
    }
  }

  if (["generate-aiml-library", "generate-dsa-question"].includes(endpoint)) {
    const concepts = form.concepts
      .split(",")
      .map((c) => c.trim())
      .filter(Boolean);
    if (concepts.length === 0) {
      errs.push("Enter at least one concept (comma separated).");
    }
  }

  if (endpoint === "generate-dsa-question") {
    if (form.dsaLanguages.length === 0) {
      errs.push("Select at least one starter language.");
    }
  }

  if (endpoint === "enrich-dsa") {
    const raw = form.enrichDsaJson.trim();
    if (!raw) {
      errs.push("Enrich DSA requires a JSON body.");
    } else {
      try {
        const parsed = JSON.parse(raw) as unknown;
        if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
          errs.push("Enrich DSA body must be a JSON object (not an array or primitive).");
        }
      } catch {
        errs.push("Enrich DSA JSON is invalid — check commas and quotes.");
      }
    }
  }

  return errs;
}
