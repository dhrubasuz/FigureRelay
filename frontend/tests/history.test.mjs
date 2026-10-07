import assert from 'node:assert/strict';
import { test } from 'node:test';
import { generationExportUrl } from '../src/api.ts';
import { approvedHistoryGeneration } from '../src/history.ts';

test('an older approval keeps its exact generation and revision when a later generation is published', () => {
  const older = { event: 'generation.approved', details: { generation_id: 'approved-older', revision: 1 } };
  const current = { event: 'generation.approved', details: { generation_id: 'approved-current', revision: 3 } };
  const approved = [current, older].map(approvedHistoryGeneration);
  assert.deepEqual(approved, [{ id: 'approved-current', revision: 3 }, { id: 'approved-older', revision: 1 }]);
  assert.equal(generationExportUrl('project', approved[1].id), '/api/projects/project/generations/approved-older/export');
});

test('preview, rejected, exported and malformed approval events never offer approved downloads', () => {
  for (const event of ['generation.previewed', 'generation.rejected', 'generation.exported']) {
    assert.equal(approvedHistoryGeneration({ event, details: { generation_id: 'generation', revision: 1 } }), null);
  }
  for (const details of [undefined, 'generation', [], {}, { generation_id: '' }, { generation_id: '  ' }, { generation_id: 7 }]) {
    assert.equal(approvedHistoryGeneration({ event: 'generation.approved', details }), null);
  }
});

test('approval revision is optional and download URLs encode identifiers as single path segments', () => {
  assert.deepEqual(approvedHistoryGeneration({ event: 'generation.approved', details: { generation_id: 'approved' } }), { id: 'approved', revision: null });
  assert.equal(generationExportUrl('project /?#', 'generation /?#'), '/api/projects/project%20%2F%3F%23/generations/generation%20%2F%3F%23/export');
});
