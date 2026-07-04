import type { Api } from "./types";
import { mockClient } from "./mockClient";
import { client } from "./client";

// The one fork point: flip VITE_USE_MOCKS=false (e.g. in apps/web/.env.local) once apps/api is
// live to switch the whole app to the real backend — no component ever imports mockClient/client
// directly, so nothing else needs to change.
const USE_MOCKS = import.meta.env.VITE_USE_MOCKS !== "false";

export const api: Api = USE_MOCKS ? mockClient : client;
