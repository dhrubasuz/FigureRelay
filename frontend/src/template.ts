import type { Template } from './api';

/** Normalize wire objects before comparison; JSON member order carries no template meaning. */
export function copyTemplate(template: Template): Template {
  return {
    title: template.title,
    sections: template.sections.map(item => ({ title: item.title, body: item.body })),
    slides: template.slides.map(item => ({ title: item.title, body: item.body })),
  };
}

export function isTemplateDirty(draft: Template, saved: Template): boolean {
  return JSON.stringify(copyTemplate(draft)) !== JSON.stringify(copyTemplate(saved));
}
