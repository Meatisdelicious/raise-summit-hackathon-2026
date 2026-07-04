import type { Api } from "./types";
import { mockClient } from "./mockClient";
import { client } from "./client";

// The one fork point. Now that apps/api is live, the DEFAULT is the real backend (via the Vite
// /api proxy). Set VITE_USE_MOCKS=true (e.g. in apps/web/.env.local) for offline, mock-only
// frontend dev. No component imports mockClient/client directly, so nothing else changes.
const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === "true";

export const api: Api = USE_MOCKS ? mockClient : client;
