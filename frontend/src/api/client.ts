/**
 * API client entry-point.
 *
 * All exports come from instrumented.ts which wraps requests with:
 * - "Server is waking up..." banner after 3 s
 * - Progress-message utilities for long-running operations
 *
 * Existing `import { api } from "../api/client"` imports continue to work.
 */
export {
  api,
  apiUrl,
  API_CONFIGURATION_ERROR,
  fetchWithRetry,
  ServerWakeUpBanner,
  useServerWakeUp,
  useProgress,
  PROGRESS_MESSAGES,
  waitForJob,
} from "./instrumented";
export type { JobStatus, ProgressKey } from "./instrumented";
