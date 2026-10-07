import { useEffect, useRef, useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { api, ApiError, formatDate, formatMetric, generationExportUrl, listProjects } from './api';
import type { Generation, HistoryEntry, Project, ProjectSummary, Template, TextBlock } from './api';
import { Badge, Brand, EmptyPanel, GenerationMeta, Icon, ReportPaper, SlideCards } from './components';
import type { IconName } from './components';
import { copyTemplate, isTemplateDirty } from './template';
import { approvedHistoryGeneration, historyGenerationId } from './history';

type Tab = 'sources' | 'report' | 'slides' | 'review' | 'history';
const tabs: { id: Tab; label: string; caption: string; icon: IconName }[] = [
  { id: 'sources', label: 'Sources', caption: 'The numbers behind your story', icon: 'sources' },
  { id: 'report', label: 'Report', caption: 'Write once. Keep every number connected.', icon: 'report' },
  { id: 'slides', label: 'Slides', caption: 'The same source, a different audience', icon: 'slides' },
  { id: 'review', label: 'Review', caption: 'See the impact before it leaves your workspace', icon: 'review' },
  { id: 'history', label: 'History', caption: 'A record of the decisions you made', icon: 'history' },
];
const blankTemplate: Template = { title: '', sections: [], slides: [] };

function displayValue(value: unknown): string {
  return value === null || value === undefined || value === '' ? '—' : String(value);
}
function historyTitle(entry: HistoryEntry): string {
  const event = entry.event ?? entry.action ?? entry.type ?? 'Project updated';
  const labels: Record<string, string> = {
    'project.created': 'Project created', 'source.imported': 'Source imported',
    'template.updated': 'Template saved', 'generation.previewed': 'Impact preview generated',
    'generation.approved': 'Generation approved', 'generation.rejected': 'Candidate rejected',
    'generation.exported': 'Generation exported',
  };
  return labels[event] ?? event.replace(/[._]/g, ' ');
}

export default function App() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [projectId, setProjectId] = useState('');
  const [project, setProject] = useState<Project | null>(null);
  const [draft, setDraft] = useState<Template>(blankTemplate);
  const [tab, setTab] = useState<Tab>('sources');
  const [health, setHealth] = useState<'connecting' | 'online' | 'offline'>('connecting');
  const [booting, setBooting] = useState(true);
  const [loadingProject, setLoadingProject] = useState(false);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [createOpen, setCreateOpen] = useState(false);
  const [projectName, setProjectName] = useState('');
  const [actor, setActor] = useState('Dhruba Poudel');
  const [acknowledged, setAcknowledged] = useState(false);
  const [exportRequest, setExportRequest] = useState<{ projectId: string; generationId: string; previousEntryIds: string[] } | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const newProjectInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([api<{ status: string }>('/health', { signal: controller.signal }), listProjects(controller.signal)])
      .then(([status, items]) => {
        setHealth(status.status === 'ok' ? 'online' : 'offline');
        setProjects(items);
        if (items.length > 0) setProjectId(items[0].id);
      })
      .catch((failure: unknown) => {
        if (controller.signal.aborted) return;
        setHealth('offline');
        setError(failure instanceof Error ? failure.message : 'Could not connect to the local service.');
      })
      .finally(() => { if (!controller.signal.aborted) setBooting(false); });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!projectId) return;
    const controller = new AbortController();
    setLoadingProject(true);
    setProject(null);
    setError('');
    api<Project>(`/projects/${encodeURIComponent(projectId)}`, { signal: controller.signal })
      .then(next => { setProject(next); setDraft(copyTemplate(next.template)); setAcknowledged(false); })
      .catch((failure: unknown) => {
        if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : 'Could not open this project.');
      })
      .finally(() => { if (!controller.signal.aborted) setLoadingProject(false); });
    return () => controller.abort();
  }, [projectId]);

  useEffect(() => { if (createOpen) newProjectInput.current?.focus(); }, [createOpen]);

  useEffect(() => {
    if (!exportRequest || exportRequest.projectId !== projectId) return;
    const request = exportRequest;
    const controller = new AbortController();
    let attempts = 0;
    let timer: number;
    async function refreshExportHistory() {
      attempts += 1;
      try {
        const next = await api<Project>(`/projects/${encodeURIComponent(request.projectId)}`, { signal: controller.signal });
        if (controller.signal.aborted) return;
        // A native download is owned by the browser. Refresh only server history;
        // never infer that its bytes reached the user's Downloads folder.
        setProject(current => current?.id === next.id ? { ...current, history: next.history } : current);
        const recorded = next.history.some(entry => entry.event === 'generation.exported' && historyGenerationId(entry) === request.generationId && entry.id && !request.previousEntryIds.includes(entry.id));
        if (!recorded && attempts < 5) timer = window.setTimeout(refreshExportHistory, 500);
      } catch (failure) {
        if (!controller.signal.aborted) {
          setError('The export was requested, but its history could not be refreshed. Reload the saved project to check the record.');
          if (failure instanceof TypeError) setHealth('offline');
        }
      }
    }
    timer = window.setTimeout(refreshExportHistory, 500);
    return () => { controller.abort(); window.clearTimeout(timer); };
  }, [exportRequest, projectId]);

  const dirty = project ? isTemplateDirty(draft, project.template) : false;
  const candidate = project?.candidate ?? null;
  const affectedChanges = candidate?.changes.filter(change => change.before !== change.after) ?? [];
  const published = project?.published ?? null;
  const candidateStale = candidate !== null && candidate.revision !== project?.revision;
  const disabled = !!busy || booting || loadingProject;
  const activeTab = tabs.find(item => item.id === tab)!;
  const projectPath = project ? `/projects/${encodeURIComponent(project.id)}` : '';

  async function run(label: string, task: () => Promise<void>) {
    setBusy(label);
    setError('');
    setNotice('');
    try {
      await task();
      setHealth('online');
    } catch (failure) {
      const message = failure instanceof Error ? failure.message : 'The action could not be completed.';
      setError(failure instanceof ApiError && failure.status === 409 ? `${message} Reload the project, then generate a fresh preview.` : message);
      if (failure instanceof TypeError) setHealth('offline');
    } finally { setBusy(''); }
  }

  async function refreshProject(id: string, preserveDraft = false): Promise<Project> {
    const next = await api<Project>(`/projects/${encodeURIComponent(id)}`);
    setProject(next);
    if (!preserveDraft) setDraft(copyTemplate(next.template));
    return next;
  }

  async function createProject(event: FormEvent) {
    event.preventDefault();
    if (!projectName.trim()) return;
    await run('Creating project', async () => {
      const created = await api<Project>('/projects', { method: 'POST', body: JSON.stringify({ name: projectName.trim() }) });
      setProjects(await listProjects());
      setProjectId(created.id);
      setProject(created);
      setDraft(copyTemplate(created.template));
      setCreateOpen(false);
      setProjectName('');
      setTab('sources');
      setNotice('Project created. Import a source to begin.');
    });
  }

  async function loadDemo() {
    await run('Loading demo', async () => {
      const created = await api<Project>('/demo', { method: 'POST' });
      setProjects(await listProjects());
      setProjectId(created.id);
      setProject(created);
      setDraft(copyTemplate(created.template));
      setTab('sources');
      setNotice('Demo loaded with sample metrics and linked templates.');
    });
  }

  async function importSource(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || !project) return;
    await run('Importing source', async () => {
      const form = new FormData();
      form.append('file', file);
      await api<Project>(`${projectPath}/sources`, { method: 'POST', body: form });
      await refreshProject(project.id, true);
      setNotice(`${file.name} imported as a staged source. Published outputs have not changed.`);
      setAcknowledged(false);
    });
  }

  async function stageDemoRevision() {
    if (!project) return;
    await run('Staging sample changes', async () => {
      await api(`${projectPath}/demo-revision`, { method: 'POST' });
      await refreshProject(project.id, true);
      setNotice('Sample revision staged. Generate a preview to see its impact.');
      setAcknowledged(false);
      setTab('review');
    });
  }

  async function saveTemplate() {
    if (!project) return;
    await run('Saving template', async () => {
      await api(`${projectPath}/template`, { method: 'PUT', body: JSON.stringify(draft) });
      await refreshProject(project.id);
      setNotice('Template saved. Generate a fresh preview to review the changes.');
      setAcknowledged(false);
    });
  }

  async function generatePreview() {
    if (!project) return;
    await run('Generating impact preview', async () => {
      let current = project;
      if (dirty) {
        await api(`${projectPath}/template`, { method: 'PUT', body: JSON.stringify(draft) });
        current = await refreshProject(project.id);
      }
      await api<Generation>(`${projectPath}/preview`, { method: 'POST', body: JSON.stringify({ expected_revision: current.revision }) });
      await refreshProject(project.id);
      setAcknowledged(false);
      setTab('review');
      setNotice('Impact preview generated. Published outputs have not changed.');
    });
  }

  async function approveCandidate() {
    if (!project || !candidate || !actor.trim()) return;
    await run('Approving generation', async () => {
      await api(`${projectPath}/generations/${encodeURIComponent(candidate.id)}/approve`, {
        method: 'POST', body: JSON.stringify({ expected_revision: project.revision, actor: actor.trim(), acknowledge_warnings: acknowledged }),
      });
      await refreshProject(project.id, true);
      setNotice('Generation approved. The published report and slides now use this snapshot.');
      setAcknowledged(false);
    });
  }

  async function rejectCandidate() {
    if (!project || !candidate || !actor.trim()) return;
    await run('Rejecting candidate', async () => {
      await api(`${projectPath}/generations/${encodeURIComponent(candidate.id)}/reject`, { method: 'POST', body: JSON.stringify({ actor: actor.trim() }) });
      await refreshProject(project.id, true);
      setNotice('Candidate rejected. Your previously published generation is unchanged.');
      setAcknowledged(false);
    });
  }

  function requestExport(generationId: string, revision: number | null) {
    if (!project) return;
    setError('');
    setNotice(`Export requested${revision !== null ? ` for approved revision ${revision}` : ' for the approved generation'}. Your browser handles the download. Office files are static snapshots.`);
    setExportRequest({ projectId: project.id, generationId, previousEntryIds: project.history.flatMap(entry => entry.id ? [entry.id] : []) });
  }

  async function reload() {
    await run('Reloading project', async () => {
      if (projectId) await refreshProject(projectId);
      else {
        const items = await listProjects();
        setProjects(items);
        if (items.length > 0) setProjectId(items[0].id);
        await api('/health');
      }
      setNotice(projectId ? 'Saved project reloaded. Unsaved template edits were reset.' : 'Local service connected.');
    });
  }

  async function switchProject(id: string) {
    if (!project || !dirty) { setProjectId(id); setNotice(''); return; }
    await run('Saving template before switching', async () => {
      await api(`${projectPath}/template`, { method: 'PUT', body: JSON.stringify(draft) });
      setProjectId(id);
      setNotice('Template saved before switching projects.');
    });
  }

  function updateBlock(kind: 'sections' | 'slides', index: number, patch: Partial<TextBlock>) {
    setDraft(current => ({ ...current, [kind]: current[kind].map((block, blockIndex) => blockIndex === index ? { ...block, ...patch } : block) }));
  }
  function addBlock(kind: 'sections' | 'slides') {
    setDraft(current => ({ ...current, [kind]: [...current[kind], { title: `${kind === 'sections' ? 'Section' : 'Slide'} ${current[kind].length + 1}`, body: '' }] }));
  }
  function removeBlock(kind: 'sections' | 'slides', index: number) {
    setDraft(current => ({ ...current, [kind]: current[kind].filter((_, blockIndex) => blockIndex !== index) }));
  }

  return <div className="app-shell">
    <a className="skip-link" href="#main-content">Skip to workspace</a>
    <aside className="sidebar">
      <Brand/>
      <div className="workspace-caption">CONNECTED REPORTING</div>
      <div className="project-picker">
        <label htmlFor="project-select">Workspace</label>
        <select id="project-select" value={projectId} disabled={disabled || projects.length === 0} onChange={event => void switchProject(event.target.value)}>
          {projects.length === 0 ? <option value="">No projects yet</option> : null}
          {projects.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
        <button className="new-project" onClick={() => setCreateOpen(current => !current)} disabled={disabled}><Icon name="plus" size={16}/>New project</button>
      </div>
      {createOpen ? <form className="create-project-form" onSubmit={createProject}>
        <label htmlFor="new-project-name">Project name</label>
        <input ref={newProjectInput} id="new-project-name" placeholder="Quarterly board report" value={projectName} maxLength={120} onChange={event => setProjectName(event.target.value)} disabled={disabled}/>
        <div className="create-actions"><button type="submit" disabled={disabled || !projectName.trim()}>Create</button><button type="button" onClick={() => setCreateOpen(false)} disabled={disabled}>Cancel</button></div>
      </form> : null}
      <nav aria-label="Workspace navigation">{tabs.map(item => <button key={item.id} className={`nav-item ${tab === item.id ? 'nav-item-active' : ''}`} aria-current={tab === item.id ? 'page' : undefined} onClick={() => setTab(item.id)} disabled={loadingProject}><Icon name={item.icon}/><span>{item.label}</span>{item.id === 'review' && candidate ? <span className="nav-dot" aria-label="Candidate available"/> : null}</button>)}</nav>
      <div className="sidebar-bottom"><div className="local-indicator"><span className={`status-dot status-${health}`}/>{health === 'online' ? 'Local service connected' : health === 'connecting' ? 'Connecting to service' : 'Service unavailable'}</div><p>Experimental · v0.1.0<br/>No sign-in or built-in cloud sync.</p><div className="maintainer">Created by Dhruba Poudel</div></div>
    </aside>

    <main className="main" id="main-content">
      <header className="topbar"><div className="breadcrumb">Workspace <Icon name="chevron" size={13}/><span>{project?.name ?? 'Getting started'}</span></div><div className="topbar-end"><span className="prototype-label">LOCAL-FIRST PROTOTYPE</span><button className="icon-button" onClick={() => setCreateOpen(current => !current)} disabled={disabled} title="Create a project" aria-label="Create a project"><Icon name="plus" size={18}/></button><button className="icon-button" onClick={reload} disabled={disabled} title="Reload saved project; resets unsaved template edits" aria-label="Reload saved project; resets unsaved template edits"><Icon name="refresh" size={18}/></button></div></header>
      <div className="content">
        <div className="page-heading"><div><div className="eyebrow">YOUR WORKSPACE, CONNECTED</div><h1>{activeTab.label}</h1><p>{activeTab.caption}</p></div><div className="page-actions">{project ? <>{published && !disabled ? <a className="button button-outline" href={generationExportUrl(project.id, published.id)} download onClick={() => requestExport(published.id, published.revision)}><Icon name="download" size={17}/>Export ZIP</a> : <button className="button button-outline" disabled><Icon name="download" size={17}/>Export ZIP</button>}<button className="button button-primary" onClick={generatePreview} disabled={disabled || project.metrics.length === 0}><Icon name="review" size={17}/>{dirty ? 'Save & preview' : 'Generate preview'}</button></> : <button className="button button-primary" onClick={loadDemo} disabled={disabled}><Icon name="spark" size={17}/>Explore the demo</button>}</div></div>

        <div className="live-status" aria-live="polite" aria-atomic="true">{busy ? <div className="message message-loading"><span className="spinner"/>{busy}…</div> : null}{notice ? <div className="message message-success"><Icon name="check" size={18}/><span>{notice}</span><button onClick={() => setNotice('')} aria-label="Dismiss notification"><Icon name="close" size={15}/></button></div> : null}</div>
        {error ? <div className="message message-error" role="alert"><Icon name="close" size={18}/><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss error"><Icon name="close" size={15}/></button></div> : null}

        {booting || loadingProject ? <div className="loading-workspace"><span className="spinner"/><p>{booting ? 'Connecting to your local workspace…' : 'Opening project…'}</p></div> : !project ? <div className="onboarding">
          <div className="onboarding-copy"><Badge tone="teal">ONE SOURCE. EVERY OCCURRENCE.</Badge><h2>The number changes.<br/><em>Your story stays together.</em></h2><p>Connect a spreadsheet value to a report and presentation. See every affected occurrence, then choose when to publish.</p><div className="onboarding-actions"><button className="button button-primary" onClick={loadDemo} disabled={disabled}><Icon name="spark" size={18}/>Try a sample project</button><button className="button button-outline" onClick={() => setCreateOpen(true)} disabled={disabled}>Create your own<Icon name="arrow" size={17}/></button></div><p className="onboarding-footnote">Sample data only. Real imports are processed by your local FigureRelay service.</p></div>
          <div className="relay-illustration" aria-hidden="true"><div className="illustration-source"><Icon name="sources"/><span>Source spreadsheet</span><strong>$12.8m</strong><small>Revenue · staged revision</small></div><div className="illustration-connector"><span/><Icon name="arrow" size={24}/><span/></div><div className="illustration-targets"><div><Icon name="report"/><span>Board report</span><strong>$12.8m</strong></div><div><Icon name="slides"/><span>Quarterly slides</span><strong>$12.8m</strong></div></div><div className="illustration-label"><Icon name="review" size={16}/>Illustration: review before publishing</div></div>
          <div className="journey-strip"><div><span>01</span><strong>Connect the source</strong><p>Give every metric a stable key.</p></div><div><span>02</span><strong>Review the impact</strong><p>Compare candidate and published values.</p></div><div><span>03</span><strong>Publish with context</strong><p>Keep the exact generation and its history.</p></div></div>
        </div> : <>
          <div className="workspace-state"><div><span className="state-label">CURRENT SOURCE</span><strong>Version {project.source_version}</strong><span>{project.metrics.length} {project.metrics.length === 1 ? 'metric' : 'metrics'}</span></div><div><span className="state-label">EDITABLE WORKSPACE</span><strong>Revision {project.revision}</strong>{dirty ? <Badge tone="amber">Unsaved template</Badge> : <span>Template saved</span>}</div><div><span className="state-label">PUBLISHED SNAPSHOT</span><strong>{published ? `Revision ${published.revision}` : 'Not published yet'}</strong><span>{published ? 'Fixed until you approve a new generation' : 'Generate a preview to begin'}</span></div></div>

          {tab === 'sources' ? <>
            <section className="source-intro"><div><div className="eyebrow">START WITH THE SOURCE</div><h2>Numbers with a place to belong.</h2><p>Import a table of named metrics. Source updates are staged; your published report and slides stay fixed until you approve a new generation.</p></div><button className="button button-primary" onClick={() => fileInput.current?.click()} disabled={disabled}><Icon name="upload" size={17}/>Import CSV or XLSX</button><input ref={fileInput} className="visually-hidden" type="file" accept=".csv,.xlsx" aria-label="Import metric source CSV or XLSX" onChange={importSource} disabled={disabled}/></section>
            <section className="panel metrics-panel"><div className="panel-header"><div><h2>Source metrics</h2><p>Stable keys connect these values to your templates.</p></div><Badge tone="teal">Source v{project.source_version}</Badge></div>{project.metrics.length > 0 ? <div className="table-scroll"><table className="metrics-table"><caption className="visually-hidden">Current staged source metrics</caption><thead><tr><th scope="col">Metric</th><th scope="col">Key</th><th scope="col">Value</th><th scope="col">Kind / unit</th><th scope="col">Period</th></tr></thead><tbody>{project.metrics.map(metric => <tr key={metric.key}><td><span className="metric-icon"><Icon name="link" size={16}/></span><strong>{metric.label}</strong></td><td><code>{metric.key}</code></td><td className="numeric-value">{formatMetric(metric)}</td><td><span className="kind-text">{metric.kind}</span>{metric.unit ? <span className="unit-label">{metric.unit}</span> : null}</td><td>{metric.period || '—'}</td></tr>)}</tbody></table></div> : <EmptyPanel title="Your first source starts here" description="Import a CSV or XLSX table with key, label, value, kind, unit and period columns." icon="sources"><button className="button button-outline" onClick={() => fileInput.current?.click()} disabled={disabled}>Choose a source file</button></EmptyPanel>}</section>
            <div className="source-bottom-grid"><section className="panel format-panel"><div className="small-icon"><Icon name="sources"/></div><h3>A simple, explicit source format</h3><p>Use these six column headers. Keep each <code>key</code> unique and stable when you update the file.</p><div className="schema-row">key, label, value, kind, unit, period</div><p className="small muted">Kinds: <code>number</code>, <code>text</code>, <code>date</code>. Unit <code>percent</code> displays <code>0.245</code> as 24.5%; unit <code>%</code> displays <code>24.5</code> as 24.5%. Currency codes stay explicit. Replace XLSX formulas with values.</p></section><section className="panel demo-panel"><Badge tone="amber">TRY THE FULL JOURNEY</Badge><h3>See a change travel.</h3><p>Load a sample project, approve its first preview, then stage the sample revision to see where the new numbers appear.</p><div className="inline-actions"><button className="button button-outline" onClick={loadDemo} disabled={disabled}><Icon name="spark" size={16}/>Load demo</button><button className="button button-soft" onClick={stageDemoRevision} disabled={disabled || project.metrics.length === 0}>Stage sample v2<Icon name="arrow" size={16}/></button></div><p className="small muted">Sample v2 replaces the current source with demo metrics.</p></section></div>
          </> : null}

          {tab === 'report' || tab === 'slides' ? <>
            <div className="editor-toolbar"><div><Badge tone="amber">DRAFT TEMPLATE</Badge><span>Use <code>{'{{key}}'}</code> to insert a source metric.</span></div><button className="button button-outline button-small" onClick={saveTemplate} disabled={disabled || !dirty}>Save template</button></div>
            <div className={`template-layout ${tab === 'slides' ? 'template-layout-slides' : ''}`}><section className="panel template-editor"><div className="panel-header"><div><h2>{tab === 'report' ? 'Report template' : 'Presentation template'}</h2><p>Saved edits appear in the next preview.</p></div><Icon name={activeTab.icon} size={22}/></div><div className="editor-fields"><label htmlFor="report-title">Report / presentation title</label><input id="report-title" value={draft.title} onChange={event => setDraft(current => ({ ...current, title: event.target.value }))} disabled={disabled} maxLength={120} placeholder="Quarterly business review"/>{(tab === 'report' ? draft.sections : draft.slides).map((block, index) => <div className="block-editor" key={index}><div className="block-label"><span>{tab === 'report' ? 'Section' : 'Slide'} {String(index + 1).padStart(2, '0')}</span><button className="text-button text-button-danger" onClick={() => removeBlock(tab === 'report' ? 'sections' : 'slides', index)} disabled={disabled} aria-label={`Remove ${tab === 'report' ? 'section' : 'slide'} ${index + 1}`}>Remove</button></div><label htmlFor={`block-title-${tab}-${index}`}>Title</label><input id={`block-title-${tab}-${index}`} value={block.title} maxLength={120} onChange={event => updateBlock(tab === 'report' ? 'sections' : 'slides', index, { title: event.target.value })} disabled={disabled}/><label htmlFor={`block-body-${tab}-${index}`}>Body</label><textarea id={`block-body-${tab}-${index}`} value={block.body} maxLength={tab === 'slides' ? 1200 : 4000} rows={tab === 'report' ? 6 : 5} onChange={event => updateBlock(tab === 'report' ? 'sections' : 'slides', index, { body: event.target.value })} placeholder={`For example: Revenue was {{revenue}} this quarter.`} disabled={disabled}/>{tab === 'slides' ? <span className="field-hint">{block.body.length} / 1,200 characters</span> : null}</div>)}<button className="add-block" onClick={() => addBlock(tab === 'report' ? 'sections' : 'slides')} disabled={disabled || (tab === 'slides' ? draft.slides.length : draft.sections.length) >= 20}><Icon name="plus" size={17}/>Add {tab === 'report' ? 'section' : 'slide'}</button>{tab === 'slides' ? <p className="small muted">Up to 20 slides, with 120-character titles and 1,200-character bodies. This preview shows text structure, not Office pagination.</p> : null}</div></section><section className="published-preview"><div className="preview-label"><span className="status-dot status-online"/><h2>Published {tab === 'report' ? 'report' : 'slides'}</h2>{published ? <Badge tone="teal">Revision {published.revision}</Badge> : null}</div>{published ? tab === 'report' ? <ReportPaper content={published.rendered}/> : <SlideCards slides={published.rendered.slides} title={published.rendered.title}/> : <EmptyPanel title="Waiting for your first approval" description="Your draft is separate from the published snapshot. Generate a preview and approve it in Review." icon={activeTab.icon}/>}</section></div><section className="token-library"><div><Icon name="link" size={17}/><strong>Available metric tokens</strong><span>Copy into a title or body.</span></div><div className="token-list">{project.metrics.map(metric => <code key={metric.key}>{`{{${metric.key}}}`}</code>)}{project.metrics.length === 0 ? <span className="muted">Import a source to add metrics.</span> : null}</div></section>
          </> : null}

          {tab === 'review' ? <>
            <section className="review-banner"><div className="review-banner-icon"><Icon name="review" size={27}/></div><div><h2>Every change deserves a clear view.</h2><p>A candidate is a frozen preview. Approval publishes that exact snapshot across the report and slides.</p></div><div className="review-status">{candidate ? <Badge tone={candidateStale ? 'red' : 'amber'}>{candidateStale ? 'Preview out of date' : `Candidate · r${candidate.revision}`}</Badge> : <Badge>No candidate yet</Badge>}</div></section>
            {!candidate ? <section className="panel"><EmptyPanel title="Ready when you are" description="Generate an impact preview from your current source and saved template. No published values change during preview." icon="review"><button className="button button-primary" onClick={generatePreview} disabled={disabled || project.metrics.length === 0}><Icon name="review" size={17}/>Generate preview</button></EmptyPanel></section> : <>
              {candidateStale ? <div className="message message-error"><Icon name="refresh" size={18}/><span>The source or template changed after this preview. Generate a new candidate before approval.</span></div> : null}
              {dirty ? <div className="message message-warning"><Icon name="report" size={18}/><span>You have unsaved template edits. Save and generate a new preview before approving.</span></div> : null}
              <div className="candidate-heading"><div><h2>Impact preview</h2><GenerationMeta generation={candidate}/></div><span className="impact-count">{affectedChanges.length}<small>affected {affectedChanges.length === 1 ? 'occurrence' : 'occurrences'}</small></span></div>
              {candidate.errors.length > 0 ? <section className="validation-list validation-errors" aria-label="Candidate errors"><h3>Resolve these errors before approval</h3><ul>{candidate.errors.map((item, index) => <li key={index}>{item}</li>)}</ul></section> : null}
              {candidate.warnings.length > 0 ? <section className="validation-list validation-warnings" aria-label="Candidate warnings"><h3>Review these warnings</h3><ul>{candidate.warnings.map((item, index) => <li key={index}>{item}</li>)}</ul></section> : null}
              <section className="panel impact-panel"><div className="panel-header"><div><h2>{published ? 'Changes from the published snapshot' : 'Your first published snapshot'}</h2><p>{published ? 'Each row identifies a linked destination affected by this candidate.' : 'This candidate establishes the initial report and slide values.'}</p></div><Badge tone="amber">FROZEN PREVIEW</Badge></div>{affectedChanges.length > 0 ? <div className="table-scroll"><table className="impact-table"><caption className="visually-hidden">Changes in the candidate generation</caption><thead><tr><th scope="col">Destination / metric</th><th scope="col">Published</th><th scope="col">Candidate</th></tr></thead><tbody>{affectedChanges.map((change, index) => <tr key={`${change.location}-${change.key}-${index}`}><td><strong>{change.label || change.key}</strong><span className="location-text">{change.location}</span>{change.key ? <code>{change.key}</code> : null}</td><td className="before-value">{displayValue(change.before)}</td><td className="after-value"><Icon name="arrow" size={16}/>{displayValue(change.after)}</td></tr>)}</tbody></table></div> : <EmptyPanel title="No changed linked occurrences" description="The candidate has no reported linked-value changes. Review its rendered report and slides before making a decision." icon="check"/>}</section>
              <details className="candidate-content"><summary><Icon name="report" size={18}/>View candidate report and slides<Icon name="chevron" size={17}/></summary><div className="candidate-rendered"><ReportPaper content={candidate.rendered} draft/><div><h3>Candidate slides</h3><SlideCards slides={candidate.rendered.slides} title={candidate.rendered.title} draft/></div></div></details>
              <section className="approval-panel"><div><div className="eyebrow">YOUR DECISION</div><h2>Publish the reviewed snapshot.</h2><p>Approval records the name you enter. This local prototype has no authentication or separate reviewer roles.</p></div><div className="approval-controls"><label htmlFor="reviewer-name">Review identity</label><input id="reviewer-name" value={actor} onChange={event => setActor(event.target.value)} maxLength={120} disabled={disabled}/>{candidate.warnings.length > 0 ? <label className="checkbox-label"><input type="checkbox" checked={acknowledged} onChange={event => setAcknowledged(event.target.checked)} disabled={disabled}/>I reviewed and acknowledge the warnings above.</label> : null}<div className="approval-actions"><button className="button button-outline" onClick={rejectCandidate} disabled={disabled || !actor.trim() || candidate.status !== 'pending'}><Icon name="close" size={17}/>Reject</button><button className="button button-primary" onClick={approveCandidate} disabled={disabled || candidateStale || dirty || candidate.errors.length > 0 || !actor.trim() || (candidate.warnings.length > 0 && !acknowledged) || candidate.status !== 'pending'}><Icon name="check" size={18}/>Approve & publish</button></div></div></section>
            </>}
          </> : null}

          {tab === 'history' ? <>
            <section className="history-intro"><div><div className="eyebrow">DECISIONS, IN CONTEXT</div><h2>Follow the work back to its source.</h2><p>Download any previously approved revision from its approval event. Project events also record imports, saved templates and previews. This is a local activity history, not an authenticated or tamper-proof audit.</p></div>{published ? <div className="history-published"><span className="status-dot status-online"/><span>Current published generation<strong>{published.id}</strong></span></div> : null}</section>
            <section className="panel history-panel"><div className="panel-header"><h2>Project activity</h2><Badge>{project.history.length} {project.history.length === 1 ? 'event' : 'events'}</Badge></div>{project.history.length > 0 ? <ol className="history-list">{project.history.map((entry, index) => {
              const approved = approvedHistoryGeneration(entry);
              const exportLabel = approved && approved.revision !== null ? `Export approved revision ${approved.revision} ZIP` : 'Export approved generation ZIP';
              return <li key={entry.id ?? `${entry.event}-${index}`}>
                <div className={`history-event-icon ${entry.event === 'generation.approved' ? 'history-approved' : ''}`}><Icon name={entry.event === 'generation.approved' ? 'check' : entry.event === 'source.imported' ? 'upload' : entry.event === 'template.updated' ? 'report' : 'history'} size={18}/></div>
                <div className="history-event-main">
                  <div className="history-event-title"><h3>{historyTitle(entry)}</h3><time dateTime={entry.created_at ?? entry.timestamp}>{formatDate(entry.created_at ?? entry.timestamp)}</time></div>
                  <p>{entry.actor ? `Recorded as ${entry.actor}` : 'Local workspace event'}{entry.revision !== undefined ? ` · Revision ${entry.revision}` : ''}</p>
                  {entry.detail ? <p>{entry.detail}</p> : null}
                  {approved ? disabled ? <button className="button button-outline button-small history-export" disabled><Icon name="download" size={15}/>{exportLabel}</button> : <a className="button button-outline button-small history-export" href={generationExportUrl(project.id, approved.id)} download onClick={() => requestExport(approved.id, approved.revision)}><Icon name="download" size={15}/>{exportLabel}</a> : null}
                  {entry.details ? <details className="event-details"><summary>Event details</summary><pre>{typeof entry.details === 'string' ? entry.details : JSON.stringify(entry.details, null, 2)}</pre></details> : null}
                </div>
              </li>;
            })}</ol> : <EmptyPanel title="Your history starts with a decision" description="Imports, template edits and generation reviews appear here." icon="history"/>}</section>
          </> : null}
        </>}
        <footer className="content-footer"><span><Brand compact/> <span>Connected numbers. Considered changes.</span></span><span>Experimental software · Dhruba Poudel</span></footer>
      </div>
    </main>
  </div>;
}
