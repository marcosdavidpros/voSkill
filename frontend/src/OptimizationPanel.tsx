import { useState } from "react";

import { createOptimizationRun, fetchOptimizerSnapshot, type OptimizationRun, type ScenarioOption } from "./api";

const metricLabels: Record<string, string> = {
  skill_gap_hours: "Lacuna ponderada de competência",
  peak_utilization: "Pico de utilização",
};

function explain(error: unknown): string {
  const code = error instanceof Error ? error.message : "Erro de execução";
  const messages: Record<string, string> = {
    FORBIDDEN: "Seu perfil não pode executar otimizações.",
    SCENARIO_NOT_FOUND: "Cenário-base não encontrado.",
    INVALID_OPTIMIZATION_INPUT: "O cenário precisa ter pessoas e demandas válidas.",
    AUTHENTICATION_REQUIRED: "Entre novamente para executar uma otimização.",
  };
  return messages[code] ?? code;
}

type OptimizationPanelProps = {
  scenarioId: string;
  scenarios: ScenarioOption[];
  onScenarioChange: (scenarioId: string) => void;
  onRunCreated: () => void;
};

type RejectedAlternative = OptimizationRun["result"]["rejected_alternatives"][number];

function groupViolations(rejected: RejectedAlternative[]) {
  const groups = new Map<string, {
    code: string;
    label: string;
    alternatives: Set<string>;
    maxAssigned: number | null;
    available: number | null;
  }>();
  for (const alternative of rejected) {
    for (const violation of alternative.violations) {
      const key = violation.constraint_id ?? violation.code;
      const label = violation.person_id && violation.period ? `${violation.person_id} · ${violation.period}` : key;
      const group = groups.get(key) ?? { code: violation.code, label, alternatives: new Set(), maxAssigned: null, available: null };
      group.alternatives.add(alternative.alternative_id);
      if (violation.assigned_hours !== undefined) {
        group.maxAssigned = Math.max(group.maxAssigned ?? 0, Number(violation.assigned_hours));
      }
      if (violation.available_hours !== undefined) group.available = Number(violation.available_hours);
      groups.set(key, group);
    }
  }
  return [...groups.entries()].sort(([, a], [, b]) => b.alternatives.size - a.alternatives.size || a.label.localeCompare(b.label));
}

export default function OptimizationPanel({ scenarioId, scenarios, onScenarioChange, onRunCreated }: OptimizationPanelProps) {
  const [seed, setSeed] = useState("42");
  const [populationSize, setPopulationSize] = useState("20");
  const [generations, setGenerations] = useState("12");
  const [run, setRun] = useState<OptimizationRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!scenarioId) return;
    setBusy(true);
    setError(null);
    setRun(null);
    try {
      const snapshot = await fetchOptimizerSnapshot(scenarioId);
      setRun(await createOptimizationRun(snapshot, Number(seed), Number(populationSize), Number(generations)));
      onRunCreated();
    } catch (caught) {
      setError(explain(caught));
    } finally {
      setBusy(false);
    }
  }

  const metadata = run?.result.run_metadata;
  const alternatives = run?.result.feasible_alternatives ?? [];

  return (
    <section className="optimization-section" aria-labelledby="optimization-heading">
      <div className="section-heading"><div><p className="eyebrow">CÁLCULO</p><h2 id="optimization-heading">Otimização do cenário</h2></div></div>
      <p className="scenario-meta">NSGA-II · execução local</p>
      <form className="optimization-form" onSubmit={submit}>
        <label>Cenário a calcular<select value={scenarioId} onChange={(event) => onScenarioChange(event.target.value)} disabled={busy || scenarios.length === 0}>
          {scenarios.length === 0 && <option value="">Nenhum cenário criado</option>}
          {scenarios.map((option) => <option key={option.scenario_id} value={option.scenario_id}>{option.project_name} · {option.scenario_name}</option>)}
        </select></label>
        <label>Seed<input type="number" min="0" step="1" value={seed} onChange={(event) => setSeed(event.target.value)} required disabled={busy} /></label>
        <label>População<input type="number" min="2" max="10000" step="1" value={populationSize} onChange={(event) => setPopulationSize(event.target.value)} required disabled={busy} /></label>
        <label>Gerações<input type="number" min="1" max="10000" step="1" value={generations} onChange={(event) => setGenerations(event.target.value)} required disabled={busy} /></label>
        <button type="submit" disabled={busy || !scenarioId}>{busy ? "Calculando…" : "Executar otimização"}</button>
      </form>
      {error && <p role="alert" className="optimization-error">{error}</p>}
      {run && <div className="optimization-result" role="region" aria-label={`Resultado da execução ${run.run_id}`}>
        <p role="status">Execução {run.run_id} · {run.result.status === "feasible" ? "Com alternativas viáveis" : "Sem alternativas viáveis."}</p>
        <dl className="optimization-premises">
          <div><dt>Snapshot</dt><dd>{metadata?.snapshot_id ?? "Não registrado"}</dd></div>
          <div><dt>Algoritmo</dt><dd>{metadata?.algorithm ?? "NSGA-II"}</dd></div>
          <div><dt>Versão</dt><dd>{run.algorithm_version}</dd></div>
          <div><dt>Seed</dt><dd>{run.seed}</dd></div>
          <div><dt>População</dt><dd>{metadata?.configuration.population_size}</dd></div>
          <div><dt>Gerações</dt><dd>{metadata?.configuration.generations}</dd></div>
        </dl>
        {alternatives.length > 0 ? <div className="table-scroll" role="region" aria-label="Alternativas calculadas" tabIndex={0}>
          <table><caption className="visually-hidden">Objetivos por alternativa; valores não são agregados num ranking</caption><thead><tr><th scope="col">Alternativa</th><th scope="col">Lacuna ponderada</th><th scope="col">Pico de utilização</th></tr></thead><tbody>
            {alternatives.map((alternative) => <tr key={alternative.alternative_id}><th scope="row">{alternative.alternative_id}</th><td>{alternative.objective_metrics.skill_gap_hours ?? "Indisponível"}</td><td>{alternative.objective_metrics.peak_utilization ?? "Indisponível"}</td></tr>)}
          </tbody></table>
        </div> : <p>Nenhuma alternativa viável foi encontrada.</p>}
        {run.result.rejected_alternatives.length > 0 && <section aria-label="Restrições das alternativas rejeitadas">
          <h3>Restrições registradas</h3>
          {run.result.status === "infeasible" && <p>Cada demanda é atribuída inteira a uma pessoa. Se a carga de uma demanda for maior que a disponibilidade mensal de qualquer pessoa do cenário, nenhuma alternativa é viável: aumente a disponibilidade, inclua mais pessoas ou reduza a demanda.</p>}
          <ul>{groupViolations(run.result.rejected_alternatives).map(([key, group]) => <li key={key}>
            {group.label} · {group.code}{group.maxAssigned !== null && group.available !== null ? `: demanda de até ${group.maxAssigned} h para ${group.available} h disponíveis` : ""} (em {group.alternatives.size} de {run.result.rejected_alternatives.length} alternativas rejeitadas)
          </li>)}</ul>
        </section>}
      </div>}
    </section>
  );
}