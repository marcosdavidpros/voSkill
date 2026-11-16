import { useEffect, useState } from "react";

import {
  fetchOperationalPlans,
  runLabel,
  type OperationalAssignment,
  type OperationalIssue,
  type OperationalPlan,
  type OperationalPlans,
  type OptimizationRunSummary,
} from "./api";
import { Pager, usePagination } from "./Pagination";

type PlanPanelProps = {
  runs: OptimizationRunSummary[];
  skillNames: Record<string, string>;
  personNames: Record<string, string>;
};

const percent = (ratio: number | null) => (ratio === null ? "—" : `${Math.round(ratio * 100)}%`);

export default function OperationalPlanPanel({ runs, skillNames, personNames }: PlanPanelProps) {
  const [runId, setRunId] = useState("");
  const [data, setData] = useState<OperationalPlans | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const newestRunId = runs[0]?.run_id ?? "";
  useEffect(() => { setRunId(newestRunId); }, [newestRunId]);

  useEffect(() => {
    if (!runId) { setData(null); return; }
    let active = true;
    setLoading(true);
    setError(null);
    fetchOperationalPlans(runId)
      .then((plans) => {
        if (!active) return;
        if (!Array.isArray(plans?.plans)) throw new Error("OPERATIONAL_PLAN_UNAVAILABLE");
        setData(plans);
        setSelectedId(plans.recommended_alternative_id ?? "");
      })
      .catch((caught: unknown) => {
        if (!active) return;
        setData(null);
        setError(caught instanceof Error ? caught.message : "OPERATIONAL_PLAN_UNAVAILABLE");
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [runId]);

  const skill = (id: string) => skillNames[id] ?? id;
  const person = (id: string) => (personNames[id] ? `${personNames[id]} (${id})` : id);
  const task = (item: { title?: string | null; skill_id?: string }) => item.title || skill(item.skill_id ?? "");
  const selected: OperationalPlan | undefined = data?.plans.find((plan) => plan.alternative_id === selectedId);
  const recommended = data?.plans.find((plan) => plan.alternative_id === data.recommended_alternative_id);
  const sortedAssignments = [...(selected?.assignments ?? [])].sort((a, b) => Number(!a.epic) - Number(!b.epic) || (a.epic ?? "").localeCompare(b.epic ?? "") || a.period.localeCompare(b.period));
  const planPages = usePagination(data?.plans ?? [], undefined, runId);
  const assignmentPages = usePagination(sortedAssignments, undefined, `${runId}/${selectedId}`);
  const slotPages = usePagination(selected?.slots ?? [], undefined, `${runId}/${selectedId}`);

  function advice(issue: OperationalIssue): string {
    if (issue.code === "overload") {
      return `${person(issue.person_id)} está com ${issue.assigned_hours} h em ${issue.period} para ${issue.available_hours} h disponíveis (${issue.excess_hours} h a mais). Aumente a disponibilidade, redistribua tarefas ou reduza a carga.`;
    }
    if (issue.code === "no_availability") {
      return `${person(issue.person_id)} recebeu ${issue.assigned_hours} h em ${issue.period}, mas não tem disponibilidade nesse mês. Informe a disponibilidade ou use outra pessoa.`;
    }
    if (issue.code === "below_level") {
      return `${task(issue)} (${issue.period}) foi para ${person(issue.person_id)}, nível ${issue.person_level} em ${skill(issue.skill_id ?? "")}; a tarefa exige ${issue.required_level}. Capacite a pessoa de ${issue.person_level} para ${issue.required_level} ou inclua alguém com nível suficiente.`;
    }
    return `${task(issue)} (${issue.period}) foi para ${person(issue.person_id)}, que não tem ${skill(issue.skill_id ?? "")} cadastrada (exige nível ${issue.required_level}). Inclua no cenário alguém com essa skill ou cadastre a competência.`;
  }

  function competency(item: OperationalAssignment): string {
    if (item.status === "ok") return `Nível ${item.person_level} (exige ${item.required_level})`;
    if (item.status === "below_level") return `Abaixo: nível ${item.person_level}, exige ${item.required_level}`;
    return `Sem a skill, exige nível ${item.required_level}`;
  }

  return (
    <section className="plan-section" aria-labelledby="plan-heading">
      <div className="section-heading"><div><p className="eyebrow">DECISÃO OPERACIONAL</p><h2 id="plan-heading">Plano operacional da alternativa</h2></div></div>
      <label className="plan-run-label">Execução
        <select value={runId} onChange={(event) => setRunId(event.target.value)} disabled={runs.length === 0}>
          {runs.length === 0 && <option value="">Nenhuma execução salva</option>}
          {runs.map((run) => <option key={run.run_id} value={run.run_id}>{runLabel(run)}</option>)}
        </select>
      </label>
      {loading && <p role="status">Montando o plano…</p>}
      {error && <p role="alert" className="plan-error">Não foi possível montar o plano: {error}</p>}
      {data && data.plans.length === 0 && <p>Esta execução não tem alternativas viáveis para detalhar.</p>}

      {data && data.uncovered_demands.length > 0 && <div className="plan-alert" role="region" aria-label="Tarefas sem cobertura no cenário">
        <h3>Tarefas que ninguém do cenário consegue cumprir</h3>
        <p>Nenhuma pessoa do cenário tem o nível exigido nestas tarefas, qualquer que seja a alternativa. Inclua alguém com a skill ou planeje a capacitação.</p>
        <ul>{data.uncovered_demands.map((item) => <li key={item.demand_id}>{task(item)} · {skill(item.skill_id)} · {item.period} · {item.load_amount} h: exige nível {item.required_level}, melhor nível no cenário {item.best_level}</li>)}</ul>
      </div>}

      {data && recommended && <>
        <div className="plan-recommendation" role="region" aria-label="Alternativa mais segura">
          <h3>Alternativa mais segura: {recommended.alternative_id}</h3>
          <p>
            {recommended.executable
              ? "Pode ser executada sem ajustes: ninguém acima da disponibilidade e todas as tarefas com a competência exigida."
              : `Ainda exige ajustes: ${recommended.summary.excess_hours} h acima da disponibilidade, ${recommended.summary.tasks_without_competency} tarefa(s) sem a competência e ${recommended.summary.tasks_below_level} abaixo do nível exigido.`}
          </p>
          <p>Critério, em ordem de desempate: {data.recommendation_rule.map((rule, index) => `${index + 1}) ${rule}`).join("; ")}. É uma sugestão para a decisão humana, não uma aprovação.</p>
        </div>

        <div className="table-scroll" role="region" aria-label="Alternativas por segurança operacional" tabIndex={0}>
          <table><caption className="visually-hidden">Alternativas ordenadas da mais segura para a menos segura</caption>
            <thead><tr><th scope="col">Alternativa</th><th scope="col">Executável</th><th scope="col">Pessoas-mês sobrecarregadas</th><th scope="col">Horas acima da disponibilidade</th><th scope="col">Pico de utilização</th><th scope="col">Tarefas sem competência</th><th scope="col">Tarefas abaixo do nível</th><th scope="col">Plano</th></tr></thead>
            <tbody>{planPages.visible.map((plan) => <tr key={plan.alternative_id} aria-selected={plan.alternative_id === selectedId}>
              <th scope="row">{plan.alternative_id}{plan.alternative_id === data.recommended_alternative_id ? " · mais segura" : ""}</th>
              <td>{plan.executable ? "Sim" : "Não"}</td>
              <td>{plan.summary.overloaded_slots + plan.summary.unavailable_slots}</td>
              <td>{plan.summary.excess_hours} h</td>
              <td>{percent(plan.summary.peak_utilization)}</td>
              <td>{plan.summary.tasks_without_competency}</td>
              <td>{plan.summary.tasks_below_level}</td>
              <td><button type="button" onClick={() => setSelectedId(plan.alternative_id)} disabled={plan.alternative_id === selectedId} aria-label={`Ver plano ${plan.alternative_id}`}>{plan.alternative_id === selectedId ? "Exibido" : "Ver plano"}</button></td>
            </tr>)}</tbody></table>
        </div>
        <Pager pagination={planPages} label="alternativas" />
      </>}

      {selected && <div className="plan-detail">
        <h3>Quem faz cada tarefa · {selected.alternative_id}</h3>
        <div className="table-scroll" role="region" aria-label="Responsáveis por tarefa" tabIndex={0}>
          <table><thead><tr><th scope="col">Épico</th><th scope="col">Tarefa</th><th scope="col">Skill</th><th scope="col">Mês</th><th scope="col">Horas</th><th scope="col">Responsável</th><th scope="col">Competência</th></tr></thead>
            <tbody>{assignmentPages.visible.map((item) => <tr key={item.demand_id} className={item.status === "ok" ? undefined : "plan-risk"}>
              <td>{item.epic ?? "Sem épico"}</td><th scope="row">{task(item)}</th><td>{skill(item.skill_id)}</td><td>{item.period}</td><td>{item.load_amount}</td><td>{person(item.person_id)}</td><td>{competency(item)}</td>
            </tr>)}</tbody></table>
        </div>
        <Pager pagination={assignmentPages} label="responsáveis por tarefa" />

        <h3>Carga por pessoa e mês</h3>
        <div className="table-scroll" role="region" aria-label="Carga por pessoa e mês" tabIndex={0}>
          <table><thead><tr><th scope="col">Pessoa</th><th scope="col">Mês</th><th scope="col">Atribuído</th><th scope="col">Disponível</th><th scope="col">Utilização</th><th scope="col">Situação</th></tr></thead>
            <tbody>{slotPages.visible.map((slot) => <tr key={`${slot.person_id}-${slot.period}`} className={slot.status === "ok" ? undefined : "plan-risk"}>
              <th scope="row">{person(slot.person_id)}</th><td>{slot.period}</td><td>{slot.assigned_hours} h</td><td>{slot.available_hours === null ? "—" : `${slot.available_hours} h`}</td><td>{percent(slot.utilization)}</td>
              <td>{slot.status === "ok" ? "Dentro da disponibilidade" : slot.status === "overloaded" ? `Sobrecarregada: ${slot.excess_hours} h a mais` : "Sem disponibilidade informada"}</td>
            </tr>)}</tbody></table>
        </div>
        <Pager pagination={slotPages} label="carga por pessoa e mês" />

        <h3>O que mudar para ficar executável</h3>
        {selected.issues.length === 0 ? <p>Nenhum ajuste necessário nesta alternativa.</p> : <ul>{selected.issues.map((issue, index) => <li key={`${issue.code}-${issue.person_id}-${issue.demand_id ?? issue.period}-${index}`}>{advice(issue)}</li>)}</ul>}
      </div>}
    </section>
  );
}
