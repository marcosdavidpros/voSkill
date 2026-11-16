import { Fragment, useEffect, useState } from "react";

import {
  createProject,
  createProjectDemand,
  deleteProjectDemand,
  fetchProjectDemands,
  fetchProjects,
  fetchSkills,
  updateProjectDemand,
  updateProject,
  type CatalogProject,
  type CatalogSkill,
  type DemandInput,
  type ProjectDemand,
} from "./api";
import { Pager, usePagination } from "./Pagination";

function messageFor(error: unknown): string {
  const code = error instanceof Error ? error.message : "Erro de conexão";
  const messages: Record<string, string> = {
    AUTHENTICATION_REQUIRED: "Entre novamente para acessar projetos.",
    FORBIDDEN: "Seu perfil pode consultar, mas não cadastrar ou alterar dados.",
    PROJECT_ALREADY_EXISTS: "Já existe um projeto com esse nome.",
    INVALID_HORIZON: "O início e o fim do horizonte devem ser no primeiro dia do mês, em ordem válida.",
    INVALID_LOAD_UNIT: "A unidade disponível neste MVP é horas.",
    UNKNOWN_SKILL: "Skill não encontrada no catálogo.",
    PERIOD_OUTSIDE_HORIZON: "O período informado está fora do horizonte do projeto.",
    DEMAND_NOT_FOUND: "A demanda não existe mais; atualize a lista.",
    PROJECT_NOT_FOUND: "O projeto não existe mais; atualize a lista.",
    HORIZON_EXCLUDES_DEMANDS: "Há demandas fora do novo horizonte. Ajuste ou exclua essas demandas antes de reduzir o horizonte.",
  };
  return messages[code] ?? code;
}

const NO_EPIC = "Sem épico";

function groupByEpic(demands: ProjectDemand[]) {
  const groups = new Map<string, ProjectDemand[]>();
  for (const demand of demands) {
    const epic = demand.epic?.trim() || NO_EPIC;
    groups.set(epic, [...(groups.get(epic) ?? []), demand]);
  }
  return [...groups.entries()]
    .sort(([a], [b]) => (a === NO_EPIC ? 1 : b === NO_EPIC ? -1 : a.localeCompare(b)))
    .map(([epic, items]) => ({
      epic,
      items: [...items].sort((a, b) => a.period.localeCompare(b.period)),
      hours: items.reduce((sum, item) => sum + Number(item.load_amount), 0),
    }));
}

export default function ProjectPanel({ part, active = true }: { part?: "projects" | "demands"; active?: boolean }) {
  const showProjects = !part || part === "projects";
  const showDemands = !part || part === "demands";
  const [projects, setProjects] = useState<CatalogProject[]>([]);
  const [skills, setSkills] = useState<CatalogSkill[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [demands, setDemands] = useState<ProjectDemand[]>([]);
  const [projectName, setProjectName] = useState("");
  const [horizonStart, setHorizonStart] = useState("");
  const [horizonEnd, setHorizonEnd] = useState("");
  const [editingProjectId, setEditingProjectId] = useState<string | null>(null);
  const [skillId, setSkillId] = useState("");
  const [level, setLevel] = useState("3");
  const [period, setPeriod] = useState("");
  const [loadAmount, setLoadAmount] = useState("");
  const [title, setTitle] = useState("");
  const [epic, setEpic] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const projectPages = usePagination(projects);
  const demandRows = groupByEpic(demands).flatMap((group) => group.items.map((demand) => ({ demand, group })));
  const demandPages = usePagination(demandRows);

  async function loadCatalogs() {
    setBusy(true);
    setError(null);
    try {
      const [nextProjects, nextSkills] = await Promise.all([fetchProjects(), fetchSkills()]);
      if (!Array.isArray(nextProjects) || !Array.isArray(nextSkills)) throw new Error("INVALID_CATALOG_RESPONSE");
      setProjects(nextProjects);
      setSkills(nextSkills);
      setLoaded(true);
      const current = nextProjects.find((item) => item.project_id === selectedProjectId) ?? nextProjects[0];
      if (current) {
        setSelectedProjectId(current.project_id);
        if (current.project_id !== selectedProjectId) setPeriod(current.horizon_start.slice(0, 7));
        setDemands(await fetchProjectDemands(current.project_id));
      }
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (active) void loadCatalogs();
  }, [active]);

  async function selectProject(projectId: string) {
    setSelectedProjectId(projectId);
    setDemands([]);
    resetDemandForm();
    const project = projects.find((item) => item.project_id === projectId);
    setPeriod(project?.horizon_start.slice(0, 7) ?? "");
    setError(null);
    if (!projectId) return;
    setBusy(true);
    try {
      setDemands(await fetchProjectDemands(projectId));
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setBusy(false);
    }
  }

  function cancelProjectEdit() {
    setEditingProjectId(null);
    setProjectName("");
    setHorizonStart("");
    setHorizonEnd("");
  }

  function startEditingProject(project: CatalogProject) {
    setEditingProjectId(project.project_id);
    setProjectName(project.project_name);
    setHorizonStart(project.horizon_start.slice(0, 7));
    setHorizonEnd(project.horizon_end.slice(0, 7));
    setMessage(null);
    setError(null);
  }

  async function submitProject(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const input = {
        project_name: projectName.trim(),
        horizon_start: `${horizonStart}-01`,
        horizon_end: `${horizonEnd}-01`,
        load_unit: "hours" as const,
      };
      if (editingProjectId) {
        const updated = await updateProject(editingProjectId, input);
        setProjects((current) => current.map((item) => item.project_id === updated.project_id ? updated : item));
        setMessage(`Projeto ${updated.project_name} atualizado.`);
        cancelProjectEdit();
        return;
      }
      const project = await createProject(input);
      const availableSkills = loaded ? skills : await fetchSkills();
      setSkills(availableSkills);
      setLoaded(true);
      setProjects((current) => [...current, project]);
      setSelectedProjectId(project.project_id);
      setDemands([]);
      resetDemandForm();
      setPeriod(project.horizon_start.slice(0, 7));
      setProjectName("");
      setMessage(`Projeto ${project.project_name} criado e selecionado.`);
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setBusy(false);
    }
  }

  async function submitDemand(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProjectId) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const input: DemandInput = {
        skill_id: skillId,
        proficiency_level: Number(level),
        period,
        load_amount: Number(loadAmount),
        load_unit: "hours",
        ...(title.trim() && { title: title.trim() }),
        ...(epic.trim() && { epic: epic.trim() }),
      };
      if (editingId) {
        const updated = await updateProjectDemand(selectedProjectId, editingId, input);
        setDemands((current) => current.map((item) => item.demand_id === editingId ? updated : item));
        setMessage("Demanda atualizada.");
        resetDemandForm();
      } else {
        const demand = await createProjectDemand(selectedProjectId, input);
        setDemands((current) => [...current, demand]);
        setMessage("Demanda registrada.");
        setSkillId("");
        setLoadAmount("");
        setTitle("");
      }
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setBusy(false);
    }
  }

  function resetDemandForm() {
    setEditingId(null);
    setSkillId("");
    setLoadAmount("");
    setTitle("");
    setEpic("");
    setLevel("3");
  }

  function startEditing(demand: ProjectDemand) {
    setEditingId(demand.demand_id);
    setSkillId(demand.skill_id);
    setLevel(String(demand.proficiency_level));
    setPeriod(demand.period);
    setLoadAmount(String(demand.load_amount));
    setTitle(demand.title ?? "");
    setEpic(demand.epic ?? "");
    setMessage(null);
    setError(null);
  }

  async function removeDemand(demand: ProjectDemand) {
    const label = demand.title || skills.find((skill) => skill.skill_id === demand.skill_id)?.skill_name || demand.skill_id;
    if (!window.confirm(`Excluir a demanda "${label}" de ${demand.period}? Cenários já salvos não mudam.`)) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await deleteProjectDemand(selectedProjectId, demand.demand_id);
      setDemands((current) => current.filter((item) => item.demand_id !== demand.demand_id));
      if (editingId === demand.demand_id) resetDemandForm();
      setMessage("Demanda excluída.");
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="project-section" aria-labelledby="project-heading">
      <div className="section-heading"><div><p className="eyebrow">PLANEJAMENTO</p><h2 id="project-heading">{part === "projects" ? "Projetos" : part === "demands" ? "Demandas" : "Projetos e demandas"}</h2></div></div>
      {!loaded && (busy ? <p role="status">Carregando projetos e skills…</p> : <button type="button" onClick={() => void loadCatalogs()}>Tentar carregar novamente</button>)}
      {error && <p className="project-error" role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
      {showProjects && <form className="project-form" onSubmit={submitProject}>
        <h3>{editingProjectId ? "Editar projeto" : "Novo projeto"}</h3>
        <label>Nome do projeto<input value={projectName} onChange={(event) => setProjectName(event.target.value)} maxLength={200} required disabled={busy} /></label>
        <label>Início do horizonte<input type="month" value={horizonStart} onChange={(event) => setHorizonStart(event.target.value)} required disabled={busy} /></label>
        <label>Fim do horizonte<input type="month" value={horizonEnd} onChange={(event) => setHorizonEnd(event.target.value)} required disabled={busy} /></label>
        <button type="submit" disabled={busy || !projectName.trim() || !horizonStart || !horizonEnd}>{editingProjectId ? "Salvar alterações" : "Criar projeto"}</button>
        {editingProjectId && <button type="button" disabled={busy} onClick={cancelProjectEdit}>Cancelar edição</button>}
      </form>}
      {part === "projects" && loaded && <div className="table-scroll" role="region" aria-label="Projetos cadastrados" tabIndex={0}>
        <table><caption className="visually-hidden">Projetos cadastrados e seus horizontes</caption><thead><tr><th scope="col">Projeto</th><th scope="col">Início</th><th scope="col">Fim</th><th scope="col">Unidade</th><th scope="col">Ação</th></tr></thead><tbody>
          {projectPages.visible.map((project) => <tr key={project.project_id}><th scope="row">{project.project_name}</th><td>{project.horizon_start.slice(0, 7)}</td><td>{project.horizon_end.slice(0, 7)}</td><td>horas</td><td><button type="button" disabled={busy} onClick={() => startEditingProject(project)} aria-label={`Editar projeto ${project.project_name}`}>Editar</button></td></tr>)}
          {projects.length === 0 && <tr><td colSpan={5}>Nenhum projeto cadastrado.</td></tr>}
        </tbody></table>
      </div>}
      {part === "projects" && loaded && <Pager pagination={projectPages} label="projetos" />}
      {showDemands && loaded && <>
        <label className="project-select-label">Projeto<select value={selectedProjectId} onChange={(event) => void selectProject(event.target.value)} disabled={busy}><option value="">Selecione um projeto</option>{projects.map((project) => <option key={project.project_id} value={project.project_id}>{project.project_name} ({project.horizon_start.slice(0, 7)} a {project.horizon_end.slice(0, 7)})</option>)}</select></label>
        {selectedProjectId && <>
          <form className="project-form" onSubmit={submitDemand}>
            <h3>{editingId ? "Editar demanda mensal" : "Nova demanda mensal"}</h3>
            <label>Épico ou história<input list="project-epics" value={epic} onChange={(event) => setEpic(event.target.value)} maxLength={200} disabled={busy} /></label>
            <datalist id="project-epics">{[...new Set(demands.map((demand) => demand.epic).filter(Boolean))].map((name) => <option key={name} value={name ?? ""} />)}</datalist>
            <label>Título da tarefa<input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={200} disabled={busy} /></label>
            <label>Skill demandada<select value={skillId} onChange={(event) => setSkillId(event.target.value)} required disabled={busy}><option value="">Selecione uma skill</option>{skills.map((skill) => <option key={skill.skill_id} value={skill.skill_id}>{skill.skill_name}</option>)}</select></label>
            <label>Nível exigido<select value={level} onChange={(event) => setLevel(event.target.value)} disabled={busy}>{[1, 2, 3, 4, 5].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
            <label>Período<input type="month" value={period} onChange={(event) => setPeriod(event.target.value)} required disabled={busy} /></label>
            <label>Carga<input type="number" min="0" step="0.01" value={loadAmount} onChange={(event) => setLoadAmount(event.target.value)} required disabled={busy} /></label>
            <span className="project-unit">Unidade: horas</span>
            <button type="submit" disabled={busy || !skillId || !period || !loadAmount}>{editingId ? "Salvar alterações" : "Registrar demanda"}</button>
            {editingId && <button type="button" disabled={busy} onClick={resetDemandForm}>Cancelar edição</button>}
          </form>
          <div className="table-scroll" role="region" aria-label="Demandas do projeto" tabIndex={0}>
            <table><caption className="visually-hidden">Demandas cadastradas do projeto, agrupadas por épico</caption><thead><tr><th scope="col">Tarefa</th><th scope="col">Skill</th><th scope="col">Nível</th><th scope="col">Período</th><th scope="col">Carga (h)</th><th scope="col">Ações</th></tr></thead><tbody>
              {demandPages.visible.map(({ demand, group }, index) => {
                const skillName = skills.find((skill) => skill.skill_id === demand.skill_id)?.skill_name ?? demand.skill_id;
                const startsGroup = index === 0 || demandPages.visible[index - 1].group.epic !== group.epic;
                return <Fragment key={demand.demand_id}>
                  {startsGroup && <tr className="epic-row"><th scope="rowgroup" colSpan={6}>{group.epic} · {group.items.length} {group.items.length === 1 ? "tarefa" : "tarefas"} · {group.hours} h</th></tr>}
                  <tr><th scope="row">{demand.title || skillName}</th><td>{skillName}</td><td>{demand.proficiency_level}</td><td>{demand.period}</td><td>{demand.load_amount}</td><td>
                    <button type="button" disabled={busy} onClick={() => startEditing(demand)} aria-label={`Editar ${demand.title || skillName} ${demand.period}`}>Editar</button>{" "}
                    <button type="button" disabled={busy} onClick={() => void removeDemand(demand)} aria-label={`Excluir ${demand.title || skillName} ${demand.period}`}>Excluir</button>
                  </td></tr>
                </Fragment>;
              })}
              {demands.length === 0 && <tr><td colSpan={6}>Nenhuma demanda cadastrada.</td></tr>}
            </tbody></table>
          </div>
          <Pager pagination={demandPages} label="demandas" />
        </>}
      </>}
    </section>
  );
}