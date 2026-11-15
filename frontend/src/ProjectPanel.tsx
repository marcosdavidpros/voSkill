import { useState } from "react";

import {
  createProject,
  createProjectDemand,
  fetchProjectDemands,
  fetchProjects,
  fetchSkills,
  type CatalogProject,
  type CatalogSkill,
  type ProjectDemand,
} from "./api";

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
  };
  return messages[code] ?? code;
}

export default function ProjectPanel() {
  const [projects, setProjects] = useState<CatalogProject[]>([]);
  const [skills, setSkills] = useState<CatalogSkill[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [demands, setDemands] = useState<ProjectDemand[]>([]);
  const [projectName, setProjectName] = useState("");
  const [horizonStart, setHorizonStart] = useState("");
  const [horizonEnd, setHorizonEnd] = useState("");
  const [skillId, setSkillId] = useState("");
  const [level, setLevel] = useState("3");
  const [period, setPeriod] = useState("");
  const [loadAmount, setLoadAmount] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function loadCatalogs() {
    setBusy(true);
    setError(null);
    try {
      const [nextProjects, nextSkills] = await Promise.all([fetchProjects(), fetchSkills()]);
      setProjects(nextProjects);
      setSkills(nextSkills);
      setLoaded(true);
      if (nextProjects.length) {
        setSelectedProjectId(nextProjects[0].project_id);
        setPeriod(nextProjects[0].horizon_start.slice(0, 7));
        setDemands(await fetchProjectDemands(nextProjects[0].project_id));
      }
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setBusy(false);
    }
  }

  async function selectProject(projectId: string) {
    setSelectedProjectId(projectId);
    setDemands([]);
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

  async function submitProject(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const project = await createProject({
        project_name: projectName.trim(),
        horizon_start: `${horizonStart}-01`,
        horizon_end: `${horizonEnd}-01`,
        load_unit: "hours",
      });
      const availableSkills = loaded ? skills : await fetchSkills();
      setSkills(availableSkills);
      setLoaded(true);
      setProjects((current) => [...current, project]);
      setSelectedProjectId(project.project_id);
      setDemands([]);
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
      const demand = await createProjectDemand(selectedProjectId, {
        skill_id: skillId,
        proficiency_level: Number(level),
        period,
        load_amount: Number(loadAmount),
        load_unit: "hours",
      });
      setDemands((current) => [...current, demand]);
      setMessage("Demanda registrada.");
      setSkillId("");
      setLoadAmount("");
    } catch (caught) {
      setError(messageFor(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="project-section" aria-labelledby="project-heading">
      <div className="section-heading"><div><p className="eyebrow">PLANEJAMENTO</p><h2 id="project-heading">Projetos e demandas</h2></div></div>
      <button type="button" disabled={busy} onClick={() => void loadCatalogs()}>{busy ? "Carregando…" : loaded ? "Atualizar projetos e skills" : "Carregar projetos e skills"}</button>
      {error && <p className="project-error" role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
      <form className="project-form" onSubmit={submitProject}>
        <h3>Novo projeto</h3>
        <label>Nome do projeto<input value={projectName} onChange={(event) => setProjectName(event.target.value)} maxLength={200} required disabled={busy} /></label>
        <label>Início do horizonte<input type="month" value={horizonStart} onChange={(event) => setHorizonStart(event.target.value)} required disabled={busy} /></label>
        <label>Fim do horizonte<input type="month" value={horizonEnd} onChange={(event) => setHorizonEnd(event.target.value)} required disabled={busy} /></label>
        <button type="submit" disabled={busy || !projectName.trim() || !horizonStart || !horizonEnd}>Criar projeto</button>
      </form>
      {loaded && <>
        <label className="project-select-label">Projeto<select value={selectedProjectId} onChange={(event) => void selectProject(event.target.value)} disabled={busy}><option value="">Selecione um projeto</option>{projects.map((project) => <option key={project.project_id} value={project.project_id}>{project.project_name} ({project.horizon_start.slice(0, 7)} a {project.horizon_end.slice(0, 7)})</option>)}</select></label>
        {selectedProjectId && <>
          <form className="project-form" onSubmit={submitDemand}>
            <h3>Nova demanda mensal</h3>
            <label>Skill demandada<select value={skillId} onChange={(event) => setSkillId(event.target.value)} required disabled={busy}><option value="">Selecione uma skill</option>{skills.map((skill) => <option key={skill.skill_id} value={skill.skill_id}>{skill.skill_name}</option>)}</select></label>
            <label>Nível exigido<select value={level} onChange={(event) => setLevel(event.target.value)} disabled={busy}>{[1, 2, 3, 4, 5].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
            <label>Período<input type="month" value={period} onChange={(event) => setPeriod(event.target.value)} required disabled={busy} /></label>
            <label>Carga<input type="number" min="0" step="0.01" value={loadAmount} onChange={(event) => setLoadAmount(event.target.value)} required disabled={busy} /></label>
            <span className="project-unit">Unidade: horas</span>
            <button type="submit" disabled={busy || !skillId || !period || !loadAmount}>Registrar demanda</button>
          </form>
          <div className="table-scroll" role="region" aria-label="Demandas do projeto" tabIndex={0}>
            <table><caption className="visually-hidden">Demandas cadastradas do projeto</caption><thead><tr><th scope="col">ID</th><th scope="col">Skill</th><th scope="col">Nível</th><th scope="col">Período</th><th scope="col">Carga</th><th scope="col">Unidade</th></tr></thead><tbody>
              {demands.map((demand) => <tr key={demand.demand_id}><th scope="row">{demand.demand_id}</th><td>{skills.find((skill) => skill.skill_id === demand.skill_id)?.skill_name ?? demand.skill_id}</td><td>{demand.proficiency_level}</td><td>{demand.period}</td><td>{demand.load_amount}</td><td>{demand.load_unit}</td></tr>)}
              {demands.length === 0 && <tr><td colSpan={6}>Nenhuma demanda cadastrada.</td></tr>}
            </tbody></table>
          </div>
        </>}
      </>}
    </section>
  );
}