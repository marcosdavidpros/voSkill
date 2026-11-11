import { useRef, useState } from "react";

import {
  fetchAlternativeComparison,
  fetchScenarioComparison,
  type AlternativeComparison,
  type ScenarioComparison,
} from "./api";
import { AlternativeComparisonResults, ScenarioComparisonResults } from "./ComparisonResults";

type ComparisonTab = "scenarios" | "alternatives";

export default function ComparisonPanel() {
  const [activeTab, setActiveTab] = useState<ComparisonTab>("scenarios");
  const [firstScenarioId, setFirstScenarioId] = useState("");
  const [secondScenarioId, setSecondScenarioId] = useState("");
  const [scenarioComparison, setScenarioComparison] = useState<ScenarioComparison | null>(null);
  const [runId, setRunId] = useState("");
  const [firstAlternativeId, setFirstAlternativeId] = useState("");
  const [secondAlternativeId, setSecondAlternativeId] = useState("");
  const [alternativeComparison, setAlternativeComparison] = useState<AlternativeComparison | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const scenarioTab = useRef<HTMLButtonElement>(null);
  const alternativeTab = useRef<HTMLButtonElement>(null);

  function handleTabKeyDown(event: React.KeyboardEvent<HTMLButtonElement>) {
    if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
    event.preventDefault();
    const nextTab = activeTab === "scenarios" ? "alternatives" : "scenarios";
    setActiveTab(nextTab);
    (nextTab === "scenarios" ? scenarioTab : alternativeTab).current?.focus();
  }

  async function submitScenarioComparison(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setScenarioComparison(null);
    try {
      setScenarioComparison(await fetchScenarioComparison(firstScenarioId.trim(), secondScenarioId.trim()));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "COMPARISON_UNAVAILABLE");
    } finally {
      setLoading(false);
    }
  }

  async function submitAlternativeComparison(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setAlternativeComparison(null);
    try {
      setAlternativeComparison(
        await fetchAlternativeComparison(runId.trim(), [firstAlternativeId.trim(), secondAlternativeId.trim()]),
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "COMPARISON_UNAVAILABLE");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="comparison-section" aria-labelledby="comparison-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">COMPARAÇÃO</p>
          <h2 id="comparison-heading">Cenários e alternativas</h2>
        </div>
      </div>

      <div className="comparison-tabs" role="tablist" aria-label="Tipo de comparação">
        <button
          ref={scenarioTab}
          id="scenario-comparison-tab"
          type="button"
          role="tab"
          aria-selected={activeTab === "scenarios"}
          aria-controls="scenario-comparison-panel"
          tabIndex={activeTab === "scenarios" ? 0 : -1}
          onClick={() => setActiveTab("scenarios")}
          onKeyDown={handleTabKeyDown}
        >
          Cenários
        </button>
        <button
          ref={alternativeTab}
          id="alternative-comparison-tab"
          type="button"
          role="tab"
          aria-selected={activeTab === "alternatives"}
          aria-controls="alternative-comparison-panel"
          tabIndex={activeTab === "alternatives" ? 0 : -1}
          onClick={() => setActiveTab("alternatives")}
          onKeyDown={handleTabKeyDown}
        >
          Alternativas
        </button>
      </div>

      {activeTab === "scenarios" ? (
        <div id="scenario-comparison-panel" role="tabpanel" aria-labelledby="scenario-comparison-tab" tabIndex={0}>
          <form className="comparison-form" onSubmit={submitScenarioComparison}>
            <label htmlFor="scenario-base-id">Cenário base<input id="scenario-base-id" value={firstScenarioId} onChange={(event) => setFirstScenarioId(event.target.value)} /></label>
            <label htmlFor="scenario-compare-id">Cenário para comparar<input id="scenario-compare-id" value={secondScenarioId} onChange={(event) => setSecondScenarioId(event.target.value)} /></label>
            <button type="submit" disabled={loading || !firstScenarioId.trim() || !secondScenarioId.trim()}>
              {loading ? "Comparando…" : "Comparar cenários"}
            </button>
          </form>
          {scenarioComparison && (
            <ScenarioComparisonResults comparison={scenarioComparison} />
          )}
        </div>
      ) : (
        <div id="alternative-comparison-panel" role="tabpanel" aria-labelledby="alternative-comparison-tab" tabIndex={0}>
          <form className="comparison-form" onSubmit={submitAlternativeComparison}>
            <label htmlFor="comparison-run-id">ID da execução<input id="comparison-run-id" value={runId} onChange={(event) => setRunId(event.target.value)} /></label>
            <label htmlFor="comparison-alt-one">Alternativa 1<input id="comparison-alt-one" value={firstAlternativeId} onChange={(event) => setFirstAlternativeId(event.target.value)} /></label>
            <label htmlFor="comparison-alt-two">Alternativa 2<input id="comparison-alt-two" value={secondAlternativeId} onChange={(event) => setSecondAlternativeId(event.target.value)} /></label>
            <button type="submit" disabled={loading || !runId.trim() || !firstAlternativeId.trim() || !secondAlternativeId.trim()}>
              {loading ? "Comparando…" : "Comparar alternativas"}
            </button>
          </form>
          {alternativeComparison && (
            <AlternativeComparisonResults comparison={alternativeComparison} />
          )}
        </div>
      )}
      {error && <p className="comparison-error" role="alert">Não foi possível comparar: {error}</p>}
    </section>
  );
}