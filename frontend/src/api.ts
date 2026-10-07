export type Metric = {
  key: string;
  label: string;
  value: number | string;
  kind: string;
  unit: string;
  period: string;
};

export type TextBlock = { title: string; body: string };
export type Template = { title: string; sections: TextBlock[]; slides: TextBlock[] };
export type Change = { key: string; label: string; location: string; before: string | number | null; after: string | number | null };
export type Generation = {
  id: string;
  revision: number;
  status: string;
  created_at: string;
  metrics: Metric[];
  rendered: Template;
  changes: Change[];
  warnings: string[];
  errors: string[];
  manifest: Record<string, unknown>;
};
export type HistoryEntry = {
  id?: string;
  generation_id?: string;
  action?: string;
  event?: string;
  type?: string;
  actor?: string;
  timestamp?: string;
  created_at?: string;
  revision?: number;
  detail?: string;
  details?: unknown;
  [key: string]: unknown;
};
export type Project = {
  id: string;
  name: string;
  revision: number;
  source_version: number;
  metrics: Metric[];
  template: Template;
  published: Generation | null;
  candidate: Generation | null;
  history: HistoryEntry[];
};
export type ProjectSummary = { id: string; name: string; revision?: number };

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const response = await fetch(`/api${path}`, { ...init, headers });
  if (!response.ok) {
    let message = `The request could not be completed (${response.status}).`;
    try {
      const payload = await response.json();
      const detail = payload.detail ?? payload.message ?? payload.error;
      if (typeof detail === 'string') message = detail;
      else if (Array.isArray(detail)) message = detail.map(item => typeof item?.msg === 'string' ? item.msg : 'Check the submitted format.').join(' ');
    } catch { /* The status is still useful when an upstream response is not JSON. */ }
    throw new ApiError(message, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export async function listProjects(signal?: AbortSignal): Promise<ProjectSummary[]> {
  const payload = await api<ProjectSummary[] | { projects: ProjectSummary[] }>('/projects', { signal });
  return Array.isArray(payload) ? payload : payload.projects;
}

export function formatMetric(metric: Metric): string {
  // Preserve imported decimal precision instead of converting financial values to floating point.
  const raw = String(metric.value);
  if (metric.kind !== 'number') return metric.unit === '%' ? `${raw}%` : metric.unit ? `${raw} ${metric.unit}` : raw;
  const match = /^([+-]?)(\d+)(?:\.(\d+))?$/.exec(raw);
  if (!match) return metric.unit ? `${raw} ${metric.unit}` : raw;
  let integer = match[2];
  let fractional = match[3] ?? '';
  if (metric.unit.toLowerCase() === 'percent') {
    const shifted = (fractional + '00').slice(0, 2);
    integer += shifted;
    fractional = fractional.slice(2);
  }
  integer = integer.replace(/^0+(?=\d)/, '');
  if (metric.unit.toLowerCase() === 'percent') fractional = fractional.replace(/0+$/, '');
  const nonzero = /[1-9]/.test(integer + fractional);
  if (!nonzero) fractional = '';
  const sign = match[1] === '-' && nonzero ? '-' : '';
  const grouped = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  const result = `${sign}${grouped}${fractional ? `.${fractional}` : ''}`;
  return metric.unit.toLowerCase() === 'percent' || metric.unit === '%' ? `${result}%` : metric.unit ? `${result} ${metric.unit}` : result;
}

export function formatDate(date: string | undefined): string {
  if (!date) return '';
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return date;
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(parsed);
}
