/**
 * CCCC Web API Client — 与 CCCC 工作组通信
 * 通过 nginx 代理，/api/v1/ 指向 CCCC Web :8858
 */

const CCCC_BASE = '/api/v1';

/** 血糖管理主工作组 */
export const MAIN_GROUP_ID = 'g_72244ae16d48';
/** 评测工作组 */
export const EVAL_GROUP_ID = 'g_deb8067ebdf7';

/**
 * CCCC access token — read from env or fallback to built-in admin token.
 * In production, set VITE_CCCC_TOKEN in .env.
 */
const CCCC_TOKEN = import.meta.env.VITE_CCCC_TOKEN || '1895';

/** Standard headers for CCCC API requests */
function ccccHeaders(extra?: Record<string, string>): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${CCCC_TOKEN}`,
    ...extra,
  };
}

// ─── Types ────────────────────────────────────────────────────────

export interface SendRequest {
  text: string;
  by?: string;
  to?: string[];
  priority?: 'normal' | 'attention';
  reply_required?: boolean;
  refs?: MedicalRef[];
}

export interface MedicalRef {
  title: string;
  type?: string;
  medical_context?: Record<string, unknown>;
  text?: string;
  [key: string]: unknown;
}

/** A ledger event from the CCCC daemon */
export interface LedgerEvent {
  id: string;
  ts: string;
  kind: string;         // "chat.message", "system.notify", "chat.read", etc.
  group_id: string;
  scope_key: string;
  by: string;           // actor_id or "user" or "system"
  data: {
    text?: string;
    to?: string[];
    priority?: string;
    reply_required?: boolean;
    reply_to?: string | null;
    refs?: MedicalRef[];
    format?: string;
    [key: string]: unknown;
  };
}

export interface GroupContext {
  ok: boolean;
  result?: {
    coordination?: Record<string, unknown>;
    agent_states?: Record<string, unknown>;
    attention?: Record<string, unknown>;
    board?: Record<string, unknown>;
    [key: string]: unknown;
  };
}

// ─── Error ─────────────────────────────────────────────────────────

export class CcccApiError extends Error {
  constructor(public status: number, public body: string) {
    super(`CCCC API error ${status}: ${body}`);
    this.name = 'CcccApiError';
  }
}

// ─── Core API ──────────────────────────────────────────────────────

/** Send a consultation message to the main medical work group */
export async function sendConsultation(
  text: string,
  patientContext?: {
    patient_id: string;
    patient_name?: string;
    profile?: Record<string, unknown>;
  },
): Promise<{ ok: boolean; event_id?: string }> {
  const refs: MedicalRef[] = [];
  if (patientContext) {
    refs.push({
      title: 'medical_context',
      medical_context: {
        patient_id: patientContext.patient_id,
        patient_name: patientContext.patient_name || 'unknown',
        profile: patientContext.profile || {},
      },
    });
  }

  const body: SendRequest = {
    text,
    by: 'user',
    to: [],             // empty → default routing (primary picks up)
    priority: 'normal',
    reply_required: true,
    refs,
  };

  const res = await fetch(`${CCCC_BASE}/groups/${MAIN_GROUP_ID}/send`, {
    method: 'POST',
    headers: ccccHeaders(),
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const errText = await res.text().catch(() => `HTTP ${res.status}`);
    throw new CcccApiError(res.status, errText);
  }

  const json = await res.json();
  // Extract event_id from response
  const eventId =
    json?.result?.event?.id ||
    json?.result?.event_id ||
    json?.event?.id ||
    '';
  return { ok: true, event_id: eventId };
}

/** Fetch recent ledger events (for page load / reconnection) */
export async function getLedgerTail(
  groupId: string = MAIN_GROUP_ID,
  lines: number = 200,
): Promise<LedgerEvent[]> {
  const res = await fetch(
    `${CCCC_BASE}/groups/${groupId}/ledger/tail?lines=${lines}&with_read_status=false`,
    { headers: ccccHeaders() },
  );
  if (!res.ok) {
    throw new CcccApiError(res.status, await res.text().catch(() => `HTTP ${res.status}`));
  }
  const json = await res.json();
  return (json?.result?.events || []) as LedgerEvent[];
}

/** Get group context for health checking */
export async function getGroupContext(
  groupId: string = MAIN_GROUP_ID,
): Promise<GroupContext> {
  const res = await fetch(`${CCCC_BASE}/groups/${groupId}/context`, {
    headers: ccccHeaders(),
  });
  if (!res.ok) {
    throw new CcccApiError(res.status, await res.text().catch(() => `HTTP ${res.status}`));
  }
  return res.json();
}

/** Ping CCCC daemon */
export async function pingDaemon(): Promise<boolean> {
  try {
    const res = await fetch(`${CCCC_BASE}/ping`, {
      headers: ccccHeaders(),
    });
    if (!res.ok) return false;
    const json = await res.json();
    return json?.ok === true;
  } catch {
    return false;
  }
}

/** Get group info (actors, state, etc.) */
export async function getGroupInfo(
  groupId: string = MAIN_GROUP_ID,
): Promise<{ ok: boolean; result?: { group?: Record<string, unknown> } }> {
  const res = await fetch(`${CCCC_BASE}/groups/${groupId}`, {
    headers: ccccHeaders(),
  });
  if (!res.ok) {
    throw new CcccApiError(res.status, await res.text().catch(() => `HTTP ${res.status}`));
  }
  return res.json();
}

/** Send an evaluation result to the CCCC eval work group to trigger self-evolution */
export async function sendEvaluation(
  evaluationId: string,
  data: {
    label: string;
    patient_id: string;
    query: string;
    safety?: string;
    personalized?: boolean;
    advice_direction?: string;
    reviewer_notes?: string;
  },
): Promise<{ ok: boolean; event_id?: string }> {
  const text = [
    `[人工评价] ${data.label}`,
    `患者: ${data.patient_id}`,
    `问题: ${data.query}`,
    data.safety ? `安全性: ${data.safety}` : '',
    data.personalized !== undefined ? `个性化: ${data.personalized ? '是' : '否'}` : '',
    data.advice_direction ? `建议方向: ${data.advice_direction}` : '',
    data.reviewer_notes ? `备注: ${data.reviewer_notes}` : '',
  ].filter(Boolean).join('\n');

  const refs: MedicalRef[] = [
    {
      title: 'evaluation_result',
      type: 'evaluation',
      medical_context: {
        evaluation_id: evaluationId,
        label: data.label,
        patient_id: data.patient_id,
        query: data.query,
        safety: data.safety,
        personalized: data.personalized,
        advice_direction: data.advice_direction,
        reviewer_notes: data.reviewer_notes,
      },
    },
  ];

  const body: SendRequest = {
    text,
    by: 'user',
    to: [],
    priority: data.label === 'BAD' || data.label === 'ERROR' ? 'attention' : 'normal',
    reply_required: false,
    refs,
  };

  const res = await fetch(`${CCCC_BASE}/groups/${EVAL_GROUP_ID}/send`, {
    method: 'POST',
    headers: ccccHeaders(),
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const errText = await res.text().catch(() => `HTTP ${res.status}`);
    throw new CcccApiError(res.status, errText);
  }

  const json = await res.json();
  const eventId =
    json?.result?.event?.id ||
    json?.result?.event_id ||
    json?.event?.id ||
    '';
  return { ok: true, event_id: eventId };
}

/** Request the eval group to run a self-evolution optimization cycle */
export async function triggerEvalEvolution(): Promise<{ ok: boolean; event_id?: string }> {
  const body: SendRequest = {
    text: '[触发自进化] 请根据最近的 BAD/ERROR 人工评价执行一轮优化（提示词优化 + 记忆强化）',
    by: 'user',
    to: [],
    priority: 'attention',
    reply_required: true,
  };

  const res = await fetch(`${CCCC_BASE}/groups/${EVAL_GROUP_ID}/send`, {
    method: 'POST',
    headers: ccccHeaders(),
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const errText = await res.text().catch(() => `HTTP ${res.status}`);
    throw new CcccApiError(res.status, errText);
  }

  const json = await res.json();
  const eventId =
    json?.result?.event?.id ||
    json?.result?.event_id ||
    json?.event?.id ||
    '';
  return { ok: true, event_id: eventId };
}

// ─── SSE Subscription ─────────────────────────────────────────────

export interface SSESubscription {
  unsubscribe: () => void;
}

/**
 * Subscribe to ledger events via SSE with auto-reconnection.
 * Uses fetch() instead of EventSource to support Authorization header.
 * The SSE endpoint is: GET /api/v1/groups/{group_id}/ledger/stream
 * Events arrive as `event: ledger\ndata: {...json...}\n\n`
 */
export function subscribeLedger(
  groupId: string = MAIN_GROUP_ID,
  onEvent: (event: LedgerEvent) => void,
  onConnectionChange?: (connected: boolean) => void,
): SSESubscription {
  let abortController: AbortController | null = null;
  let disposed = false;
  let retryCount = 0;
  let retryTimer: ReturnType<typeof setTimeout> | null = null;
  const MAX_RETRIES = 20;
  const BASE_DELAY_MS = 1000;

  async function connect() {
    if (disposed) return;

    abortController = new AbortController();
    const url = `${CCCC_BASE}/groups/${groupId}/ledger/stream`;

    try {
      const res = await fetch(url, {
        headers: {
          Authorization: `Bearer ${CCCC_TOKEN}`,
          Accept: 'text/event-stream',
          'Cache-Control': 'no-cache',
        },
        signal: abortController.signal,
      });

      if (!res.ok) {
        throw new Error(`SSE HTTP ${res.status}`);
      }
      if (!res.body) {
        throw new Error('SSE response has no body');
      }

      retryCount = 0;
      onConnectionChange?.(true);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (!disposed) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        // Keep the last incomplete line in buffer
        buffer = lines.pop() || '';

        let currentEventType = '';
        let currentData = '';

        for (const line of lines) {
          if (line.startsWith('event:')) {
            currentEventType = line.slice(6).trim();
          } else if (line.startsWith('data:')) {
            currentData = line.slice(5).trim();
          } else if (line === '' && currentData) {
            // End of an SSE event block
            if (currentEventType === 'ledger' || currentEventType === '' || currentEventType === 'message') {
              try {
                const event = JSON.parse(currentData) as LedgerEvent;
                onEvent(event);
              } catch {
                // ignore parse errors
              }
            }
            currentEventType = '';
            currentData = '';
          }
          // Skip comment lines (starting with ':')
        }
      }
    } catch (err) {
      if (disposed) return;
      // AbortError is expected on unsubscribe
      if (err instanceof DOMException && err.name === 'AbortError') return;
    }

    // Connection lost — schedule reconnect
    onConnectionChange?.(false);
    if (!disposed && retryCount < MAX_RETRIES) {
      const delay = Math.min(BASE_DELAY_MS * Math.pow(2, retryCount), 30_000);
      retryCount++;
      retryTimer = setTimeout(connect, delay);
    }
  }

  connect();

  return {
    unsubscribe: () => {
      disposed = true;
      if (retryTimer) clearTimeout(retryTimer);
      abortController?.abort();
      abortController = null;
    },
  };
}
