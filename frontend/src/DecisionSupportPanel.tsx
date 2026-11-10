import { useState } from "react";

import { fetchAlternativeExplanation, type AlternativeExplanation } from "./api";

function formatMetric(value: unknown): string {
  if (typeof value === "number") {
    return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(value);
  }
  if (typeof value === "object" && value !== null && "status" in value && value.status === "unavailable") {
    return "Indisponível";
  }
  return String(value);
}

export default function DecisionSupportPanel() {
  const [runId, setRunId] = useState("");
  const [alternativeId, setAlternativeId] = useState("");
  const [explanation, setExplanation] = useState<AlternativeExplanation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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
          ID da execução
          <input
            id="optimization-run-id"
            value={runId}
            onChange={(event) => setRunId(event.target.value)}
            autoComplete="off"
          />
        </label>
        <label htmlFor="alternative-id">
          ID da alternativa
          <input
            id="alternative-id"
            value={alternativeId}
            onChange={(event) => setAlternativeId(event.target.value)}
            autoComplete="off"
          />
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
          <dl className="decision-metrics">
            {Object.entries(explanation.metrics).map(([name, value]) => (
              <div key={name}>
                <dt>{name.replaceAll("_", " ")}</dt>
                <dd>{formatMetric(value)}</dd>
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