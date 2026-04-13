const SESSION_COOKIE_NAME = "gisul_admin_session";
const SESSION_TTL_SECONDS = 7 * 24 * 60 * 60;

type AdminSessionPayload = {
  sub: "admin";
  iat: number;
  exp: number;
};

const textEncoder = new TextEncoder();
const textDecoder = new TextDecoder();

function getSessionSecret(): string {
  return (
    process.env.ADMIN_SESSION_SECRET?.trim() ||
    process.env.ADMIN_TOKEN?.trim() ||
    ""
  );
}

function bytesToBase64Url(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function base64UrlToBytes(value: string): Uint8Array {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, "=");
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

function constantTimeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) {
    return false;
  }
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) {
    diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return diff === 0;
}

async function importSigningKey(secret: string): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    "raw",
    textEncoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
}

async function signValue(value: string, secret: string): Promise<string> {
  const key = await importSigningKey(secret);
  const signature = await crypto.subtle.sign(
    "HMAC",
    key,
    textEncoder.encode(value)
  );
  return bytesToBase64Url(new Uint8Array(signature));
}

export function getAdminSessionCookieName(): string {
  return SESSION_COOKIE_NAME;
}

export function getAdminSessionExpiryDate(now = new Date()): Date {
  return new Date(now.getTime() + SESSION_TTL_SECONDS * 1000);
}

export async function createAdminSessionToken(nowSeconds?: number): Promise<string> {
  const secret = getSessionSecret();
  if (!secret) {
    throw new Error("Admin session secret is not configured");
  }

  const issuedAt = nowSeconds ?? Math.floor(Date.now() / 1000);
  const payload: AdminSessionPayload = {
    sub: "admin",
    iat: issuedAt,
    exp: issuedAt + SESSION_TTL_SECONDS,
  };
  const encodedPayload = bytesToBase64Url(
    textEncoder.encode(JSON.stringify(payload))
  );
  const signature = await signValue(encodedPayload, secret);
  return `${encodedPayload}.${signature}`;
}

export async function verifyAdminSessionToken(
  token: string | undefined | null
): Promise<boolean> {
  if (!token) {
    return false;
  }

  const secret = getSessionSecret();
  if (!secret) {
    return false;
  }

  const [encodedPayload, providedSignature, ...rest] = token.split(".");
  if (!encodedPayload || !providedSignature || rest.length > 0) {
    return false;
  }

  let payload: AdminSessionPayload;
  try {
    const payloadJson = textDecoder.decode(base64UrlToBytes(encodedPayload));
    payload = JSON.parse(payloadJson) as AdminSessionPayload;
  } catch {
    return false;
  }

  if (payload.sub !== "admin") {
    return false;
  }
  if (!Number.isInteger(payload.iat) || !Number.isInteger(payload.exp)) {
    return false;
  }
  const nowSeconds = Math.floor(Date.now() / 1000);
  if (payload.exp <= nowSeconds || payload.iat > payload.exp) {
    return false;
  }

  const expectedSignature = await signValue(encodedPayload, secret);
  return constantTimeEqual(providedSignature, expectedSignature);
}
