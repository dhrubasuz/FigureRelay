import type { HistoryEntry } from './api';

export function historyGenerationId(entry: HistoryEntry): string | null {
  if (!entry.details || typeof entry.details !== 'object' || Array.isArray(entry.details)) return null;
  const id = (entry.details as Record<string, unknown>).generation_id;
  return typeof id === 'string' && id.trim() ? id : null;
}

export function approvedHistoryGeneration(entry: HistoryEntry): { id: string; revision: number | null } | null {
  if (entry.event !== 'generation.approved') return null;
  const id = historyGenerationId(entry);
  if (!id) return null;
  const details = entry.details as Record<string, unknown>;
  const revision = details.revision ?? entry.revision;
  return { id, revision: typeof revision === 'number' && Number.isInteger(revision) && revision >= 0 ? revision : null };
}
