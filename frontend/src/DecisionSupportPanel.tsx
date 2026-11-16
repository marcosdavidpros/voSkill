import { useState } from "react";

import { fetchAlternativeExplanation, runLabel, type AlternativeExplanation, type OptimizationRunSummary } from "./api";

function formatMetric(value: unknown): string {
  if (typeof value === "number") {
    return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(value);
  }
  if (typeof value === "object" && value !== null && "status" in value && value.status === "unavailable") {
    const reason = "reason" in value && typeof value.reason === "string" ? `: ${value.reason}` : "";
    return `Indisponível${reason}`;
  }
  return String(value);
}

export default function DecisionSupportPanel({ runs }: { runs: OptimizationRunSummary[] }) {
  const [runId, setRunId] = useState("");
  const [alternativeId, setAlternativeId] = useState("");
  const [explanation, setExplanation] = useState<AlternativeExplanation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const alternativesOfRun = runs.find((run) => run.run_id === runId)?.alternative_ids ?? [];
  const directionGroups = Object.entries(explanation?.metric_definitions ?? {}).reduce<Record<string, string[]>>(
    (groups, [name, definition]) => {
      groups[definition.direction] ??= [];
      groups[definition.direction].push(definition.label || name);
      return groups;
    },
    {},
  );

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setExplanation(null);
    try {
      setExplanation(await fetchAlternativeExplanation(runId.trim(), alternativeId.trim()));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "EXPLANATION_UNAVAILABLE");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="decision-support" aria-labelledby="decision-support-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">SUPERVISÃO HUMANA</p>
          <h2 id="decision-support-heading">Explicação da alternativa</h2>
        </div>
      </div>
      <form className="alternative-lookup" onSubmit={submit}>
        <label htmlFor="optimization-run-id">
          Execução
          <select
            id="optimization-run-id"
            value={runId}
            onChange={(event) => { setRunId(event.target.value); setAlternativeId(""); }}
            disabled={runs.length === 0}
          >
            <option value="">{runs.length === 0 ? "Nenhuma execução salva" : "Selecione a execução"}</option>
            {runs.map((run) => <option key={run.run_id} value={run.run_id}>{runLabel(run)}</option>)}
          </select>
        </label>
        <label htmlFor="alternative-id">
          Alternativa
          <select
            id="alternative-id"
            value={alternativeId}
            onChange={(event) => setAlternativeId(event.target.value)}
            disabled={alternativesOfRun.length === 0}
          >
            <option value="">Selecione a alternativa</option>
            {alternativesOfRun.map((id) => <option key={id} value={id}>{id}</option>)}
          </select>
        </label>
        <button type="submit" disabled={loading || !runId.trim() || !alternativeId.trim()}>
          {loading ? "Consultando…" : "Consultar explicação"}
        </button>
      </form>

      {error && <p className="decision-message" role="alert">Não foi possível carregar: {error}</p>}
      {explanation && (
        <article className="decision-result" aria-label={`Alternativa ${explanation.alternative_id}`}>
          <div className="decision-status">
            <strong>Apoio à decisão</strong>
            <span>Pendente de aprovação humana</span>
          </div>
          <p className="scenario-meta">
            Execução {explanation.run_id} · Alternativa {explanation.alternative_id} · Snapshot {explanation.snapshot_id}
          </p>
          {Object.entries(directionGroups).map(([direction, labels]) => (
            <p className="metric-direction-summary" key={direction}>
              Direção: {direction === "minimize" ? "Minimizar" : "Maximizar"} · {labels.join(", ")}
            </p>
          ))}
          <dl className="decision-metrics">
            {Object.entries(explanation.metrics).map(([name, value]) => (
              <div key={name}>
                <dt>{explanation.metric_definitions?.[name]?.label ?? name.replaceAll("_", " ")}</dt>
                <dd>{formatMetric(value)}</dd>
                <dd className="metric-context">
                  {explanation.metric_definitions?.[name] ? (
                    <>
                      <span>{explanation.metric_definitions[name].definition}</span>
                      <span>Unidade: {explanation.metric_definitions[name].unit}</span>
                      <span>Fonte: {explanation.metric_definitions[name].source}</span>
                    </>
                  ) : (
                    <span>Definição indisponível.</span>
                  )}
                </dd>
              </div>
            ))}
          </dl>
          {explanation.narrative.text ? (
            <p>{explanation.narrative.text}</p>
          ) : (
            <p className="muted-value" role="status">Narrativa indisponível.</p>
          )}
          {explanation.uncertainty && (
            <p className="decision-message" role="status">A explicação contém dados indisponíveis ou incerteza.</p>
          )}
        </article>
      )}
    </section>
  );
}