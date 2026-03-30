import type { EndpointId, PlaygroundFormState } from "./buildPayload";

/** Build query string to restore a subset of the form via /playground?... */
export function buildPlaygroundShareSearchParams(
  endpoint: EndpointId,
  form: PlaygroundFormState
): string {
  const p = new URLSearchParams();
  p.set("endpoint", endpoint);
  p.set("topic", form.topic);
  p.set("difficulty", form.difficulty);
  p.set("numQuestions", String(form.numQuestions));
  if (form.orgId.trim()) p.set("orgId", form.orgId.trim());
  if (form.concepts.trim()) p.set("concepts", form.concepts);
  if (form.targetAudience.trim()) p.set("targetAudience", form.targetAudience);
  if (form.language) p.set("language", form.language);
  if (form.databaseType) p.set("databaseType", form.databaseType);
  if (endpoint === "generate-topics") {
    p.set("assessmentTitle", form.assessmentTitle);
    p.set("skills", form.skills);
    p.set("experienceMin", String(form.experienceMin));
    p.set("experienceMax", String(form.experienceMax));
  }
  if (["generate-coding", "generate-sql"].includes(endpoint)) {
    p.set("jobRole", form.jobRole);
    p.set("experienceYears", form.experienceYears);
  }
  if (endpoint === "generate-dsa-question" && form.dsaLanguages.length > 0) {
    p.set("dsaLangs", form.dsaLanguages.join(","));
  }
  return p.toString();
}

/** Apply share params from URL into form state (partial). */
export function hydrateFormFromSearchParams(
  searchParams: URLSearchParams,
  form: PlaygroundFormState
): PlaygroundFormState {
  const next = { ...form };
  const g = (k: string) => searchParams.get(k);
  const topic = g("topic");
  if (topic != null) next.topic = topic;
  const diff = g("difficulty");
  if (diff != null && ["Easy", "Medium", "Hard"].includes(diff)) next.difficulty = diff;
  const nq = g("numQuestions");
  if (nq != null) {
    const n = parseInt(nq, 10);
    if (n >= 1 && n <= 20) next.numQuestions = n;
  }
  const concepts = g("concepts");
  if (concepts != null) next.concepts = concepts;
  const aud = g("targetAudience");
  if (aud != null) next.targetAudience = aud;
  const lang = g("language");
  if (lang != null) next.language = lang;
  const db = g("databaseType");
  if (db != null) next.databaseType = db;
  const at = g("assessmentTitle");
  if (at != null) next.assessmentTitle = at;
  const skills = g("skills");
  if (skills != null) next.skills = skills;
  const emin = g("experienceMin");
  if (emin != null) next.experienceMin = Number(emin);
  const emax = g("experienceMax");
  if (emax != null) next.experienceMax = Number(emax);
  const jr = g("jobRole");
  if (jr != null) next.jobRole = jr;
  const ey = g("experienceYears");
  if (ey != null) next.experienceYears = ey;
  const langs = g("dsaLangs");
  if (langs != null) {
    const list = langs
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (list.length > 0) next.dsaLanguages = list;
  }
  const oid = g("orgId");
  if (oid != null) next.orgId = oid;
  return next;
}
