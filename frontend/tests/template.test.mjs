import assert from 'node:assert/strict';
import { test } from 'node:test';
import { copyTemplate, isTemplateDirty } from '../src/template.ts';

const importedTemplate = {
  sections: [{ body: 'Revenue was {{revenue}}.', title: 'Performance' }],
  slides: [{ body: 'Revenue: {{revenue}}', title: 'Quarter at a glance' }],
  title: 'Quarterly review',
};

test('a freshly loaded template stays saved even when the API orders JSON fields differently', () => {
  const editorTemplate = {
    title: 'Quarterly review',
    sections: [{ title: 'Performance', body: 'Revenue was {{revenue}}.' }],
    slides: [{ title: 'Quarter at a glance', body: 'Revenue: {{revenue}}' }],
  };
  assert.equal(isTemplateDirty(editorTemplate, importedTemplate), false);
  assert.equal(isTemplateDirty(copyTemplate(importedTemplate), importedTemplate), false);
});

test('a real body edit is unsaved and cannot be mistaken for the saved review candidate', () => {
  const editedTemplate = copyTemplate(importedTemplate);
  editedTemplate.sections[0].body = 'Revenue was {{revenue}}; results are preliminary.';
  assert.equal(isTemplateDirty(editedTemplate, importedTemplate), true);
  assert.equal(importedTemplate.sections[0].body, 'Revenue was {{revenue}}.');
});
