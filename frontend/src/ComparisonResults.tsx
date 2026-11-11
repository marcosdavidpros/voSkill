import type { AlternativeComparison, ScenarioComparison } from "./api";

function displayValue(value: unknown): string {
  if (value === null || value === undefined) return "Não informado";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function displayMetric(metric: { status: string; value?: number; reason?: string; unit?: string }): string {
  if (metric.status === "unavailable") {
    return `Indisponível: ${metric.reason ?? "motivo não informado"}`;
  }
  return `${metric.value ?? "Não informado"}${metric.unit ? ` ${metric.unit}` : ""}`;
}

export function ScenarioComparisonResults({ comparison }: { comparison: ScenarioComparison }) {
  return (
    <section className="comparison-results" aria-label="Comparação de cenários">
      <ul className="comparison-statuses">
        {comparison.scenarios.map((scenario) => (
          <li key={scenario.scenario_id}>
            <strong>{scenario.scenario_id}</strong>: <span>{scenario.status === "complete" ? "Completo" : "Incompleto"}</span>
            {scenario.missing.map((item) => (
              <span className="comparison-missing" key={`${scenario.scenario_id}-${item.period}-${item.field}`}>
                Ausente: {item.period} · {item.field}
              </span>
            ))}
          </li>
        ))}
      </ul>
      <div
        className="comparison-table-scroll"
        role="region"
        aria-label="Tabela de comparação de cenários"
        tabIndex={0}
      >
        <table>
          <caption>Premissas e diferenças por período</caption>
          <thead>
            <tr>
              <th scope="col">Período</th>
              <th scope="col">Premissa</th>
              <th scope="col">{comparison.scenario_ids[0]}</th>
              <th scope="col">{comparison.scenario_ids[1]}</th>
              <th scope="col">Estado</th>
            </tr>
          </thead>
          <tbody>
            {comparison.periods.flatMap((period) => {
              const assumptions = comparison.scenario_ids.map((scenarioId) => {
                const value = period.assumptions[scenarioId];
                return value && typeof value === "object" ? value as Record<string, unknown> : {};
              });
              const fields = [...new Set(assumptions.flatMap((value) => Object.keys(value)))].sort();
              return fields.map((field) => {
                const changed = field in period.changed_values;
                return (
                  <tr key={`${period.period}-${field}`}>
                    <th scope="row">{period.period}</th>
                    <td>{field.replaceAll("_", " ")}</td>
                    <td>{displayValue(assumptions[0][field])}</td>
                    <td>{displayValue(assumptions[1][field])}</td>
                    <td>{changed ? "Alterada" : "Sem alteração"}</td>
                  </tr>
                );
              });
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function AlternativeComparisonResults({ comparison }: { comparison: AlternativeComparison }) {
  return (
    <section className="comparison-results" aria-label="Comparação de alternativas">
      <div
        className="comparison-table-scroll"
        role="region"
        aria-label="Tabela de comparação de alternativas"
        tabIndex={0}
      >
        <table>
          <caption>Métricas independentes por alternativa</caption>
          <thead>
            <tr>
              <th scope="col">Alternativa</th>
              <th scope="col">Objetivo</th>
              <th scope="col">Valor</th>
              <th scope="col">Unidade</th>
              <th scope="col">Fonte</th>
            </tr>
          </thead>
          <tbody>
            {comparison.alternatives.flatMap((alternative) =>
              Object.entries(alternative.objective_metrics).map(([name, metric]) => {
                const definition = comparison.metric_definitions[name];
                return (
                  <tr key={`${alternative.alternative_id}-${name}`}>
                    <th scope="row">{alternative.alternative_id}</th>
                    <td>{definition?.label ?? name.replaceAll("_", " ")}</td>
                    <td>{displayMetric(metric)}</td>
                    <td>{metric.status === "available" ? metric.unit ?? definition?.unit ?? "Unidade não informada" : "—"}</td>
                    <td>{metric.status === "available" ? metric.source ?? definition?.source ?? "Fonte não informada" : "—"}</td>
                  </tr>
                );
              }),
            )}
          </tbody>
        </table>
      </div>
      <h3>Trade-off</h3>
      {comparison.trade_offs.length === 0 ? (
        <p>Nenhum trade-off identificado entre os objetivos.</p>
      ) : (
        <ul>
          {comparison.trade_offs.map((tradeOff) => (
            <li key={tradeOff.alternative_ids.join("-")}>
              {tradeOff.alternative_ids.join(" / ")}: {tradeOff.objectives.map((name) => comparison.metric_definitions[name]?.label ?? name).join(" · ")}
            </li>
          ))}
        </ul>
      )}
      <section className="run-premises" aria-label="Premissas da execução">
        <h3>Premissas da execução</h3>
        <dl>
          <div><dt>Snapshot</dt><dd>{comparison.run_premises.snapshot_id ?? "Não registrado"}</dd></div>
          <div><dt>Algoritmo</dt><dd>{comparison.run_premises.algorithm ?? "Não registrado"}</dd></div>
          <div><dt>Versão</dt><dd>{comparison.run_premises.algorithm_version ?? "Não registrada"}</dd></div>
          <div><dt>Seed</dt><dd>{comparison.run_premises.seed ?? "Não registrada"}</dd></div>
          <div><dt>Objetivos</dt><dd>{displayValue(comparison.run_premises.configuration.objectives)}</dd></div>
          <div><dt>População</dt><dd>{displayValue(comparison.run_premises.configuration.population_size)}</dd></div>
          <div><dt>Gerações</dt><dd>{displayValue(comparison.run_premises.configuration.generations)}</dd></div>
        </dl>
        <h4>Restrições avaliadas</h4>
        <p>{comparison.constraint_trace.checked_hard_constraints.length > 0
          ? comparison.constraint_trace.checked_hard_constraints.join(" · ")
          : "Nenhuma restrição avaliada registrada."}</p>
        {comparison.constraint_trace.rejected_alternatives.length === 0 ? (
          <p>Nenhuma violação de restrição registrada.</p>
        ) : (
          <ul>
            {comparison.constraint_trace.rejected_alternatives.flatMap((alternative) =>
              alternative.violations.map((violation) => (
                <li key={`${alternative.alternative_id}-${violation.constraint_id}`}>
                  {alternative.alternative_id}: {violation.code} · {violation.person_id ?? "Pessoa não informada"} · {violation.period ?? "Período não informado"} · {violation.assigned_hours ?? "Carga não informada"}/{violation.available_hours ?? "Disponibilidade não informada"}
                </li>
              )),
            )}
          </ul>
        )}
      </section>
    </section>
  );
}