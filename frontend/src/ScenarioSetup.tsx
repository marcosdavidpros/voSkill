import { useEffect, useState } from "react";

import {
  createBaseScenario,
  fetchPeople,
  fetchProjectDemands,
  fetchProjects,
  fetchScenarios,
  fetchSkills,
  fetchOptimizerSnapshot,
  updateBaseScenario,
  type CatalogPerson,
  type CatalogProject,
  type ProjectDemand,
  type ScenarioOption,
} from "./api";
import { Pager, usePagination } from "./Pagination";

function explain(error: unknown): string {
  const code = error instanceof Error ? error.message : "Erro de conexão";
  const messages: Record<string, string> = {
    FORBIDDEN: "Seu perfil não pode criar cenários.",
    PROJECT_HAS_NO_DEMANDS: "Cadastre pelo menos uma demanda antes de montar o cenário.",
    PERSON_NOT_FOUND: "Uma das pessoas selecionadas não está mais ativa.",
    MISSING_AVAILABILITY: "Informe a disponibilidade em todos os meses com demanda.",
    PERIOD_OUTSIDE_HORIZON: "A disponibilidade está fora do horizonte do projeto.",
    SCENARIO_ALREADY_EXISTS: "Já existe um cenário com esse nome no projeto.",
    SCENARIO_HAS_ALTERNATIVES: "Este cenário já tem alternativas geradas e não pode ser alterado. Salve como novo cenário.",
    SCENARIO_NOT_EDITABLE: "Somente cenários-base podem ser editados.",
  };
  return messages[code] ?? code;
}

type ScenarioSetupProps = {
  onCreated: (scenarioId: string) => void;
  active?: boolean;
};

export default function ScenarioSetup({ onCreated, active = true }: ScenarioSetupProps) {
  const [projects, setProjects] = useState<CatalogProject[]>([]);
  const [people, setPeople] = useState<CatalogPerson[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [demands, setDemands] = useState<ProjectDemand[]>([]);
  const [skillNames, setSkillNames] = useState<Record<string, string>>({});
  const [selectedPeople, setSelectedPeople] = useState<string[]>([]);
  const [availability, setAvailability] = useState<Record<string, Record<string, string>>>({});
  const [scenarioName, setScenarioName] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<{ scenarioName: string; updated: boolean } | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioOption[]>([]);
  const [editingId, setEditingId] = useState("");
  const demandPages = usePagination(demands);
  const demandPeriods = [...new Set(demands.map((demand) => demand.period))].sort();
  const projectScenarios = scenarios.filter((scenario) => scenario.project_id === selectedProjectId && scenario.scenario_type === "BASE");

  async function reloadScenarios() {
    const loadedScenarios = await fetchScenarios().catch(() => []);
    setScenarios(Array.isArray(loadedScenarios) ? loadedScenarios : []);
  }

  async function loadCatalogs() {
    setBusy(true);
    setError(null);
    try {
      const [nextProjects, nextPeople, nextSkills] = await Promise.all([fetchProjects(), fetchPeople(), fetchSkills().catch(() => [])]);
      if (!Array.isArray(nextProjects) || !Array.isArray(nextPeople)) throw new Error("INVALID_CATALOG_RESPONSE");
      await reloadScenarios();
      setProjects(nextProjects);
      setPeople(nextPeople);
      setSkillNames(Array.isArray(nextSkills) ? Object.fromEntries(nextSkills.map((skill) => [skill.skill_id, skill.skill_name])) : {});
      setLoaded(true);
    } catch (caught) {
      setError(explain(caught));
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
    setSelectedPeople([]);
    setAvailability({});
    setEditingId("");
    setScenarioName("");
    setCreated(null);
    if (!projectId) return;
    setBusy(true);
    setError(null);
    try {
      setDemands(await fetchProjectDemands(projectId));
    } catch (caught) {
      setError(explain(caught));
    } finally {
      setBusy(false);
    }
  }

  function togglePerson(personId: string, checked: boolean) {
    setSelectedPeople((current) => checked ? [...current, personId] : current.filter((id) => id !== personId));
    setAvailability((current) => ({
      ...current,
      [personId]: current[personId] ?? Object.fromEntries(demandPeriods.map((period) => [period, ""])),
    }));
  }

  async function selectScenarioToEdit(scenarioId: string) {
    setEditingId(scenarioId);
    setCreated(null);
    setError(null);
    if (!scenarioId) {
      setScenarioName("");
      setSelectedPeople([]);
      setAvailability({});
      return;
    }
    setBusy(true);
    try {
      const snapshot = await fetchOptimizerSnapshot(scenarioId);
      setScenarioName(scenarios.find((scenario) => scenario.scenario_id === scenarioId)?.scenario_name ?? "");
      const activeProfiles = snapshot.profiles.filter((profile) => people.some((person) => person.person_id === profile.person_id));
      setSelectedPeople(activeProfiles.map((profile) => profile.person_id));
      setAvailability(Object.fromEntries(activeProfiles.map((profile) => [
        profile.person_id,
        Object.fromEntries(demandPeriods.map((period) => [period, profile.availability[period]?.toString() ?? ""])),
      ])));
    } catch (caught) {
      setError(explain(caught));
    } finally {
      setBusy(false);
    }
  }

  function fillAllPeriods(personId: string, hours: string) {
    setAvailability((current) => ({ ...current, [personId]: Object.fromEntries(demandPeriods.map((period) => [period, hours])) }));
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selectedProjectId) return;
    setBusy(true);
    setError(null);
    setCreated(null);
    try {
      const participants = selectedPeople.map((personId) => ({
        person_id: personId,
        availability: Object.fromEntries(
          demandPeriods.map((period) => [period, Number(availability[personId]?.[period])]),
        ),
      }));
      const result = editingId
        ? await updateBaseScenario(editingId, scenarioName.trim(), participants)
        : await createBaseScenario(selectedProjectId, scenarioName.trim(), participants);
      setCreated({ scenarioName: result.scenario_name, updated: Boolean(editingId) });
      setEditingId(result.scenario_id);
      await reloadScenarios();
      onCreated(result.scenario_id);
    } catch (caught) {
      setError(explain(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="scenario-setup" aria-labelledby="scenario-setup-heading">
      <div className="section-heading"><div><p className="eyebrow">CENÁRIO-BASE</p><h2 id="scenario-setup-heading">Disponibilidade e cenário</h2></div></div>
      {!loaded && (busy ? <p role="status">Carregando projetos e pessoas…</p> : <button type="button" onClick={() => void loadCatalogs()}>Tentar carregar novamente</button>)}
      {error && <p role="alert" className="scenario-setup-error">{error}</p>}
      {created && <p role="status">Cenário "{created.scenarioName}" {created.updated ? "atualizado" : "salvo"}. Ele já está disponível nos seletores de cenário.</p>}
      {loaded && <>
        <label className="scenario-setup-project">Projeto<select value={selectedProjectId} onChange={(event) => void selectProject(event.target.value)} disabled={busy}><option value="">Selecione um projeto</option>{projects.map((project) => <option key={project.project_id} value={project.project_id}>{project.project_name}</option>)}</select></label>
        {selectedProjectId && <form className="scenario-setup-form" onSubmit={submit}>
          <label>Cenário<select value={editingId} onChange={(event) => void selectScenarioToEdit(event.target.value)} disabled={busy}>
            <option value="">Novo cenário</option>
            {projectScenarios.map((scenario) => <option key={scenario.scenario_id} value={scenario.scenario_id}>{scenario.scenario_name}</option>)}
          </select></label>
          <label>Nome do cenário-base<input value={scenarioName} onChange={(event) => setScenarioName(event.target.value)} maxLength={200} required disabled={busy} /></label>
          {demands.length === 0 ? <p>Nenhuma demanda no projeto. Cadastre demandas antes de montar o cenário.</p> : <div className="scenario-demands">
            <h3>Demandas do projeto</h3>
            <p>Horas que o projeto precisa de cada skill, por mês. O cenário-base compara essas demandas com a carga horária das pessoas selecionadas abaixo.</p>
            <table><thead><tr><th>Épico / tarefa</th><th>Skill</th><th>Nível exigido</th><th>Mês</th><th>Carga</th></tr></thead>
              <tbody>{demandPages.visible.map((demand) => <tr key={demand.demand_id}><td>{[demand.epic, demand.title].filter(Boolean).join(" · ") || "—"}</td><td>{skillNames[demand.skill_id] ? `${skillNames[demand.skill_id]} (${demand.skill_id})` : demand.skill_id}</td><td>{demand.proficiency_level}</td><td>{demand.period}</td><td>{demand.load_amount} {demand.load_unit === "hours" ? "h" : demand.load_unit}</td></tr>)}</tbody></table>
            <Pager pagination={demandPages} label="demandas do projeto" />
          </div>}
          <fieldset disabled={busy}><legend>Participantes</legend>
            {people.map((person) => <div className="scenario-participant" key={person.person_id}>
              <label><input type="checkbox" checked={selectedPeople.includes(person.person_id)} onChange={(event) => togglePerson(person.person_id, event.target.checked)} />{person.person_id} · {person.display_name}</label>
              {selectedPeople.includes(person.person_id) && <label key={editingId}>Carga horária mensal {person.person_id} (horas, aplica a todos os meses)<input type="number" min="0" step="0.01" onChange={(event) => fillAllPeriods(person.person_id, event.target.value)} /></label>}
              {selectedPeople.includes(person.person_id) && demandPeriods.map((period) => <label key={`${person.person_id}-${period}`}>Disponibilidade {person.person_id} em {period} (horas)<input type="number" min="0" step="0.01" required value={availability[person.person_id]?.[period] ?? ""} onChange={(event) => setAvailability((current) => ({ ...current, [person.person_id]: { ...current[person.person_id], [period]: event.target.value } }))} /></label>)}
            </div>)}
          </fieldset>
          <button type="submit" disabled={busy || !scenarioName.trim() || !selectedPeople.length || !demands.length}>{editingId ? "Salvar alterações" : "Salvar cenário-base"}</button>
        </form>}
      </>}
    </section>
  );
}