import { useState } from "react";

import {
  createBaseScenario,
  fetchPeople,
  fetchProjectDemands,
  fetchProjects,
  type CatalogPerson,
  type CatalogProject,
  type ProjectDemand,
} from "./api";

function explain(error: unknown): string {
  const code = error instanceof Error ? error.message : "Erro de conexão";
  const messages: Record<string, string> = {
    FORBIDDEN: "Seu perfil não pode criar cenários.",
    PROJECT_HAS_NO_DEMANDS: "Cadastre pelo menos uma demanda antes de montar o cenário.",
    PERSON_NOT_FOUND: "Uma das pessoas selecionadas não está mais ativa.",
    MISSING_AVAILABILITY: "Informe a disponibilidade em todos os meses com demanda.",
    PERIOD_OUTSIDE_HORIZON: "A disponibilidade está fora do horizonte do projeto.",
    SCENARIO_ALREADY_EXISTS: "Já existe um cenário com esse nome no projeto.",
  };
  return messages[code] ?? code;
}

type ScenarioSetupProps = {
  onCreated: (scenarioId: string) => void;
};

export default function ScenarioSetup({ onCreated }: ScenarioSetupProps) {
  const [projects, setProjects] = useState<CatalogProject[]>([]);
  const [people, setPeople] = useState<CatalogPerson[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState("");
  const [demands, setDemands] = useState<ProjectDemand[]>([]);
  const [selectedPeople, setSelectedPeople] = useState<string[]>([]);
  const [availability, setAvailability] = useState<Record<string, Record<string, string>>>({});
  const [scenarioName, setScenarioName] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<{ scenarioId: string; snapshotId: string } | null>(null);

  async function loadCatalogs() {
    setBusy(true);
    setError(null);
    try {
      const [nextProjects, nextPeople] = await Promise.all([fetchProjects(), fetchPeople()]);
      setProjects(nextProjects);
      setPeople(nextPeople);
      setLoaded(true);
    } catch (caught) {
      setError(explain(caught));
    } finally {
      setBusy(false);
    }
  }

  async function selectProject(projectId: string) {
    setSelectedProjectId(projectId);
    setDemands([]);
    setSelectedPeople([]);
    setAvailability({});
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
      [personId]: current[personId] ?? Object.fromEntries(demands.map((demand) => [demand.period, ""])),
    }));
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
          demands.map((demand) => [demand.period, Number(availability[personId]?.[demand.period])]),
        ),
      }));
      const result = await createBaseScenario(selectedProjectId, scenarioName.trim(), participants);
      setCreated({ scenarioId: result.scenario_id, snapshotId: result.snapshot_id });
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
      <button type="button" disabled={busy} onClick={() => void loadCatalogs()}>{busy ? "Carregando…" : loaded ? "Atualizar projetos e pessoas" : "Carregar projetos e pessoas"}</button>
      {error && <p role="alert" className="scenario-setup-error">{error}</p>}
      {created && <p role="status">Cenário {created.scenarioId} salvo · Snapshot {created.snapshotId}</p>}
      {loaded && <>
        <label className="scenario-setup-project">Projeto<select value={selectedProjectId} onChange={(event) => void selectProject(event.target.value)} disabled={busy}><option value="">Selecione um projeto</option>{projects.map((project) => <option key={project.project_id} value={project.project_id}>{project.project_name}</option>)}</select></label>
        {selectedProjectId && <form className="scenario-setup-form" onSubmit={submit}>
          <label>Nome do cenário-base<input value={scenarioName} onChange={(event) => setScenarioName(event.target.value)} maxLength={200} required disabled={busy} /></label>
          <fieldset disabled={busy}><legend>Participantes</legend>
            {people.map((person) => <div className="scenario-participant" key={person.person_id}>
              <label><input type="checkbox" checked={selectedPeople.includes(person.person_id)} onChange={(event) => togglePerson(person.person_id, event.target.checked)} />{person.person_id} · {person.display_name}</label>
              {selectedPeople.includes(person.person_id) && demands.map((demand) => <label key={`${person.person_id}-${demand.period}`}>Disponibilidade {person.person_id} em {demand.period} (horas)<input type="number" min="0" step="0.01" required value={availability[person.person_id]?.[demand.period] ?? ""} onChange={(event) => setAvailability((current) => ({ ...current, [person.person_id]: { ...current[person.person_id], [demand.period]: event.target.value } }))} /></label>)}
            </div>)}
          </fieldset>
          {demands.length === 0 ? <p>Nenhuma demanda no projeto. Cadastre demandas antes de montar o cenário.</p> : <ul>{demands.map((demand) => <li key={demand.demand_id}>{demand.demand_id} · {demand.skill_id} · nível {demand.proficiency_level} · {demand.period} · {demand.load_amount} {demand.load_unit}</li>)}</ul>}
          <button type="submit" disabled={busy || !scenarioName.trim() || !selectedPeople.length || !demands.length}>Salvar cenário-base</button>
        </form>}
      </>}
    </section>
  );
}