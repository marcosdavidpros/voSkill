import { lazy, Suspense, useEffect, useState } from "react";

import {
  fetchCompetencyMap,
  fetchRiskPanel,
  saveCriticalSkillThreshold,
  type CompetencyMap,
  type RiskPanel as RiskPanelData,
} from "./api";
import DecisionSupportPanel from "./DecisionSupportPanel";
import RiskPanel from "./RiskPanel";

const Plot = lazy(() => import("react-plotly.js"));

const statusLabels = {
  confirmed: "Confirmada",
  inferred: "Inferida",
  uncovered: "Sem cobertura",
} as const;

const statusOrder = ["confirmed", "inferred", "uncovered"] as const;

export default function App() {
  const [scenarioId, setScenarioId] = useState("S-001");
  const [competencyMap, setCompetencyMap] = useState<CompetencyMap | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [riskPanel, setRiskPanel] = useState<RiskPanelData | null>(null);
  const [riskPanelError, setRiskPanelError] = useState<string | null>(null);
  const [riskSaving, setRiskSaving] = useState(false);
  const [riskSavedMessage, setRiskSavedMessage] = useState<string | null>(null);

  async function loadMap(requestedScenarioId: string) {
    setLoading(true);
    setError(null);
    setRiskPanel(null);
    setRiskPanelError(null);
    try {
      const map = await fetchCompetencyMap(requestedScenarioId);
      setCompetencyMap(map);
      try {
        setRiskPanel(await fetchRiskPanel(requestedScenarioId));
      } catch (caught) {
        setRiskPanelError(caught instanceof Error ? caught.message : "RISK_PANEL_UNAVAILABLE");
      }
    } catch (caught) {
      setCompetencyMap(null);
      setError(caught instanceof Error ? caught.message : "Não foi possível carregar o cenário.");
    } finally {
      setLoading(false);
    }
  }

  async function saveRiskThreshold(skillId: string, threshold: number) {
    if (!competencyMap) return;
    setRiskSaving(true);
    setRiskPanelError(null);
    setRiskSavedMessage(null);
    try {
      await saveCriticalSkillThreshold(competencyMap.project_id, skillId, threshold);
      setRiskPanel(await fetchRiskPanel(competencyMap.scenario_id));
      setRiskSavedMessage("Limiar salvo.");
    } catch (caught) {
      setRiskPanelError(caught instanceof Error ? caught.message : "INVALID_RISK_THRESHOLD");
    } finally {
      setRiskSaving(false);
    }
  }

  useEffect(() => {
    void loadMap("S-001");
  }, []);

  const statusCounts = statusOrder.map((status) =>
    competencyMap?.skills.filter((skill) => skill.status === status).length ?? 0,
  );
  const coverageText = competencyMap
    ? `${competencyMap.coverage.confirmed_count} de ${competencyMap.coverage.skill_count} skills com cobertura confirmada`
    : "Selecione um cenário para consultar a cobertura";

  function submitScenario(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void loadMap(scenarioId.trim());
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="wordmark" href="#main" aria-label="voSkill, ir ao conteúdo">
          <span className="wordmark-mark" aria-hidden="true">v</span>
          <span>voSkill</span>
        </a>
        <span className="topbar-section">Planejamento de competências</span>
        <span className="environment-label">MVP</span>
      </header>

      <main id="main" className="main-content">
        <div className="page-heading">
          <div>
            <p className="eyebrow">MAPA DO CENÁRIO</p>
            <h1>Cobertura de competências</h1>
            <p className="page-description">
              Competências confirmadas, inferências revisáveis e skills sem cobertura.
            </p>
          </div>
          <form className="scenario-form" onSubmit={submitScenario}>
            <label htmlFor="scenario-id">Cenário</label>
            <input
              id="scenario-id"
              name="scenarioId"
              value={scenarioId}
              onChange={(event) => setScenarioId(event.target.value)}
              autoComplete="off"
            />
            <button type="submit" disabled={loading || !scenarioId.trim()}>
              {loading ? "Carregando…" : "Carregar mapa"}
            </button>
          </form>
        </div>

        {error && (
          <div className="error-message" role="alert">
            <strong>Não foi possível abrir o mapa.</strong>
            <span>{error}</span>
          </div>
        )}

        <section className="coverage-band" aria-labelledby="coverage-heading">
          <div>
            <p className="eyebrow">COBERTURA CONFIRMADA</p>
            <h2 id="coverage-heading" role="status">{coverageText}</h2>
          </div>
          <div className="coverage-ratio" aria-label={`Cobertura confirmada: ${Math.round((competencyMap?.coverage.ratio ?? 0) * 100)} por cento`}>
            <span>{Math.round((competencyMap?.coverage.ratio ?? 0) * 100)}%</span>
            <span>confirmada</span>
          </div>
        </section>

        {competencyMap && (
          <>
            <section className="map-section" aria-labelledby="distribution-heading">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">DISTRIBUIÇÃO</p>
                  <h2 id="distribution-heading">Estados por skill</h2>
                </div>
                <p className="scenario-meta">
                  Projeto {competencyMap.project_id} <span aria-hidden="true">·</span> Cenário {competencyMap.scenario_id}
                </p>
              </div>
              <div
                className="chart-frame"
                role="img"
                aria-label={`Resumo visual: ${statusCounts[0]} skills confirmadas, ${statusCounts[1]} inferidas e ${statusCounts[2]} sem cobertura`}
              >
                <Suspense fallback={<p role="status">Carregando gráfico…</p>}>
                  <Plot
                    data={[
                      {
                        type: "bar",
                        orientation: "h",
                        x: statusCounts,
                        y: statusOrder.map((status) => statusLabels[status]),
                        marker: { color: ["#126b59", "#a95d19", "#68747b"] },
                        text: statusCounts.map(String),
                        textposition: "outside",
                        hovertemplate: "%{y}: %{x}<extra></extra>",
                      },
                    ]}
                    layout={{
                      autosize: true,
                      height: 190,
                      margin: { l: 150, r: 36, t: 12, b: 28 },
                      paper_bgcolor: "#fbfcfa",
                      plot_bgcolor: "#fbfcfa",
                      font: { family: "Arial, sans-serif", color: "#20302d", size: 12 },
                      xaxis: {
                        dtick: 1,
                        rangemode: "tozero",
                        gridcolor: "#e4e9e5",
                        title: { text: "Quantidade de skills" },
                      },
                      yaxis: { automargin: true },
                      showlegend: false,
                    }}
                    config={{ displayModeBar: false, responsive: true }}
                    useResizeHandler
                    style={{ width: "100%", height: "100%" }}
                  />
                </Suspense>
              </div>
            </section>

            <section className="table-section" aria-labelledby="skills-heading">
              <div className="section-heading table-heading">
                <div>
                  <p className="eyebrow">EVIDÊNCIAS</p>
                  <h2 id="skills-heading">Skills do cenário</h2>
                </div>
                <span className="row-count">{competencyMap.skills.length} skills</span>
              </div>
              <div
                className="table-scroll"
                role="region"
                aria-label="Tabela de cobertura de competências"
                tabIndex={0}
              >
                <table>
                  <caption className="visually-hidden">
                    Estado, cobertura e evidências por skill no cenário selecionado
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">Skill</th>
                      <th scope="col">Estado</th>
                      <th scope="col">Cobertura confirmada</th>
                      <th scope="col">Pessoa e evidência</th>
                    </tr>
                  </thead>
                  <tbody>
                    {competencyMap.skills.map((skill) => (
                      <tr key={skill.skill_id}>
                        <th scope="row">{skill.holders.find((holder) => holder.skill_name)?.skill_name ?? skill.skill_id}</th>
                        <td>
                          <span className={`status-label status-${skill.status}`}>
                            <span className="status-marker" aria-hidden="true" />
                            {statusLabels[skill.status]}
                          </span>
                        </td>
                        <td>{skill.confirmed_count} pessoa(s)</td>
                        <td>
                          {skill.holders.length === 0 ? (
                            <span className="muted-value">Nenhuma evidência confirmada</span>
                          ) : (
                            <ul className="evidence-list">
                              {skill.holders.map((holder) => (
                                <li key={`${skill.skill_id}-${holder.person_id}-${holder.status}`}>
                                  <span className="person-id">{holder.person_id}</span>
                                  {holder.status === "confirmed" ? (
                                    <span>{holder.proficiency_level}/5 · {holder.evidence}</span>
                                  ) : (
                                    <span>
                                      Inferida · {Math.round((holder.confidence ?? 0) * 100)}% de confiança · {holder.review_state}
                                    </span>
                                  )}
                                </li>
                              ))}
                            </ul>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
            <RiskPanel
              key={competencyMap.scenario_id}
              competencyMap={competencyMap}
              panel={riskPanel}
              error={riskPanelError}
              savedMessage={riskSavedMessage}
              saving={riskSaving}
              onSave={saveRiskThreshold}
            />
          </>
        )}
        <DecisionSupportPanel />
      </main>
    </div>
  );
}