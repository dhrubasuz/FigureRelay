import type { CSSProperties } from 'react';
import type { Generation, Template, TextBlock } from './api';
import { formatDate } from './api';

export type IconName = 'sources' | 'report' | 'slides' | 'review' | 'history' | 'arrow' | 'plus' | 'upload' | 'check' | 'close' | 'download' | 'spark' | 'link' | 'chevron' | 'refresh';
const paths: Record<IconName, React.ReactNode> = {
  sources: <><ellipse cx="12" cy="5" rx="7" ry="3"/><path d="M5 5v7c0 4 14 4 14 0V5M5 12v7c0 4 14 4 14 0v-7"/></>,
  report: <><path d="M7 3h7l4 4v14H7zM14 3v5h4M10 12h5M10 16h5"/></>,
  slides: <><rect x="3" y="4" width="18" height="13" rx="2"/><path d="M12 17v4M8 21h8M7 9h10M7 12h6"/></>,
  review: <><path d="M6 4h12v17H6zM9 4V2h6v2M9 11l2 2 4-4M9 17h6"/></>,
  history: <><path d="M4 9a8 8 0 1 1-.1 6M4 4v5h5M12 7v5l3 2"/></>,
  arrow: <><path d="M4 12h16M14 6l6 6-6 6"/></>,
  plus: <path d="M12 5v14M5 12h14"/>,
  upload: <><path d="M12 16V3M7 8l5-5 5 5M4 15v6h16v-6"/></>,
  check: <path d="m5 12 4 4L19 6"/>,
  close: <path d="m6 6 12 12M18 6 6 18"/>,
  download: <><path d="M12 3v13M7 11l5 5 5-5M4 17v4h16v-4"/></>,
  spark: <><path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z"/></>,
  link: <><path d="m10 14 4-4M8 15l-2 2a3 3 0 0 1-4-4l4-4a3 3 0 0 1 4 0M16 9l2-2a3 3 0 0 1 4 4l-4 4a3 3 0 0 1-4 0"/></>,
  chevron: <path d="m9 5 7 7-7 7"/>,
  refresh: <><path d="M20 7v5h-5M4 17v-5h5M19 12a7 7 0 0 0-12-5L4 10M5 12a7 7 0 0 0 12 5l3-3"/></>,
};

export function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>;
}

export function Brand({ compact = false }: { compact?: boolean }) {
  return <div className={`brand ${compact ? 'brand-compact' : ''}`}>
    <span className="brand-mark" aria-hidden="true"><span/><span/><span/></span>
    <span>Figure<span className="brand-relay">Relay</span></span>
  </div>;
}

export function Badge({ children, tone = 'neutral' }: { children: React.ReactNode; tone?: 'neutral' | 'teal' | 'amber' | 'red' }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function EmptyPanel({ title, description, icon = 'link', children }: { title: string; description: string; icon?: IconName; children?: React.ReactNode }) {
  return <div className="empty-panel"><div className="empty-icon"><Icon name={icon} size={26}/></div><h3>{title}</h3><p>{description}</p>{children}</div>;
}

export function GenerationMeta({ generation }: { generation: Generation }) {
  return <div className="generation-meta"><Badge tone={generation.status === 'approved' ? 'teal' : 'amber'}>{generation.status}</Badge><span>Revision {generation.revision}</span><span>{formatDate(generation.created_at)}</span></div>;
}

export function ReportPaper({ content, draft = false }: { content: Template; draft?: boolean }) {
  return <article className={`report-paper ${draft ? 'report-paper-draft' : ''}`}><div className="paper-label">FIGURERELAY / {draft ? 'CANDIDATE' : 'PUBLISHED REPORT'}</div><h2>{content.title || 'Untitled report'}</h2><div className="paper-rule"/>{content.sections.map((section, index) => <section key={index}><h3>{section.title}</h3><p>{section.body}</p></section>)}{content.sections.length === 0 ? <p className="muted">This report has no sections.</p> : null}<footer>Rendered text preview · exports use a separate Office layout</footer></article>;
}

export function SlideCards({ slides, title, draft = false }: { slides: TextBlock[]; title: string; draft?: boolean }) {
  return <div className="slide-grid">{slides.map((slide, index) => <article key={index} className={`slide-card ${index % 2 ? 'slide-light' : ''}`} style={{ '--slide-order': index } as CSSProperties}><div className="slide-eyebrow">{draft ? 'CANDIDATE' : 'PUBLISHED'} / {String(index + 1).padStart(2, '0')}</div><h3>{slide.title}</h3><p>{slide.body}</p><footer><span>{title}</span><span className="slide-footmark" aria-hidden="true">↗</span></footer></article>)}{slides.length === 0 ? <EmptyPanel title="No slides yet" description="Add a slide to the draft template, then generate a preview." icon="slides"/> : null}</div>;
}
