import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import OperationalPlanPanel from "./OperationalPlanPanel";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const runs = [{ run_id: "RUN-1", created_at: "2026-11-16T04:37:00Z", scenario_name: "EquipeSatPush", project_name: "SatPush", alternative_ids: ["A-002", "A-001"] }];
const skillNames = { "SK-1": "Java", "SK-2": "APIs", "SK-3": "Mensageria" };
const personNames = { "P-001": "Ana Paula", "P-002": "Thiago" };

const task = (demand_id: string, title: string | null, skill_id: string, person_id: string, person_level: number, status: string) => ({
  demand_id, title, epic: title ? "Pagamentos" : null, skill_id, period: "2026-01", load_amount: 80, required_level: 2, person_id, person_level, status,
});

const plans = {
  run_id: "RUN-1",
  snapshot_id: "SNP-1",
  recommended_alternative_id: "A-002",
  recommendation_rule: ["Menor excesso de horas acima da disponibilidade", "Menos tarefas sem ninguém com a competência"],
  uncovered_demands: [{ demand_id: "D-3", title: "Fila de eventos", epic: "Pagamentos", skill_id: "SK-3", period: "2026-01", load_amount: 30, required_level: 1, best_level: 0 }],
  plans: [
    {
      alternative_id: "A-002",
      executable: false,
      summary: { tasks: 1, tasks_ok: 0, tasks_below_level: 0, tasks_without_competency: 1, overloaded_slots: 0, unavailable_slots: 0, excess_hours: 0, peak_utilization: 0.9, skill_gap_hours: 150 },
      assignments: [task("D-2", null, "SK-2", "P-002", 0, "no_competency")],
      slots: [{ person_id: "P-002", period: "2026-01", assigned_hours: 80, available_hours: 100, utilization: 0.8, status: "ok", excess_hours: 0 }],
      issues: [{ code: "no_competency", demand_id: "D-2", title: null, epic: null, skill_id: "SK-2", period: "2026-01", person_id: "P-002", person_level: 0, required_level: 2 }],
    },
    {
      alternative_id: "A-001",
      executable: false,
      summary: { tasks: 1, tasks_ok: 1, tasks_below_level: 0, tasks_without_competency: 0, overloaded_slots: 1, unavailable_slots: 0, excess_hours: 40, peak_utilization: 1.4, skill_gap_hours: 90 },
      assignments: [task("D-1", "Integração com fila", "SK-1", "P-001", 3, "ok")],
      slots: [{ person_id: "P-001", period: "2026-01", assigned_hours: 140, available_hours: 100, utilization: 1.4, status: "overloaded", excess_hours: 40 }],
      issues: [{ code: "overload", person_id: "P-001", period: "2026-01", assigned_hours: 140, available_hours: 100, excess_hours: 40 }],
    },
  ],
};

function stubPlans(body: unknown = plans, ok = true) {
  const fetchMock = vi.fn(async () => ({ ok, status: ok ? 200 : 404, json: async () => body }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

it("answers who does each task, who is overloaded and what to change for the safest alternative", async () => {
  const fetchMock = stubPlans();
  render(<OperationalPlanPanel runs={runs} skillNames={skillNames} personNames={personNames} />);

  expect(await screen.findByRole("heading", { name: "Alternativa mais segura: A-002" })).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith("/api/optimization-runs/RUN-1/operational-plan", expect.objectContaining({ method: "GET" }));

  const owners = screen.getByRole("region", { name: "Responsáveis por tarefa" });
  const row = within(owners).getByRole("row", { name: /APIs APIs 2026-01 80 Thiago \(P-002\) Sem a skill, exige nível 2/ });
  expect(row).toBeInTheDocument();

  const todo = screen.getByRole("heading", { name: "O que mudar para ficar executável" }).nextElementSibling as HTMLElement;
  expect(within(todo).getByText(/Thiago \(P-002\), que não tem APIs cadastrada/)).toBeInTheDocument();
});

it("lists tasks nobody in the scenario can cover, independent of the alternative", async () => {
  stubPlans();
  render(<OperationalPlanPanel runs={runs} skillNames={skillNames} personNames={personNames} />);

  const alert = await screen.findByRole("region", { name: "Tarefas sem cobertura no cenário" });
  expect(within(alert).getByText(/Fila de eventos · Mensageria · 2026-01 · 30 h: exige nível 1, melhor nível no cenário 0/)).toBeInTheDocument();
});

it("shows overload per person and month and switches the detailed plan", async () => {
  const user = userEvent.setup();
  stubPlans();
  render(<OperationalPlanPanel runs={runs} skillNames={skillNames} personNames={personNames} />);

  await screen.findByRole("heading", { name: "Alternativa mais segura: A-002" });
  await user.click(screen.getByRole("button", { name: "Ver plano A-001" }));

  const load = screen.getByRole("region", { name: "Carga por pessoa e mês" });
  expect(within(load).getByRole("row", { name: /Ana Paula \(P-001\) 2026-01 140 h 100 h 140% Sobrecarregada: 40 h a mais/ })).toBeInTheDocument();
  expect(screen.getByText(/Ana Paula \(P-001\) está com 140 h em 2026-01 para 100 h disponíveis \(40 h a mais\)/)).toBeInTheDocument();
  expect(screen.getByRole("rowheader", { name: "Integração com fila" })).toBeInTheDocument();

  const ranking = screen.getByRole("region", { name: "Alternativas por segurança operacional" });
  const rows = within(ranking).getAllByRole("row");
  expect(rows[1]).toHaveTextContent("A-002 · mais segura");
  expect(rows[2]).toHaveTextContent("A-001");
  expect(rows[2]).toHaveTextContent("40 h");
});

it("tells the user when the run has no feasible alternatives and reports load errors", async () => {
  stubPlans({ ...plans, recommended_alternative_id: null, uncovered_demands: [], plans: [] });
  render(<OperationalPlanPanel runs={runs} skillNames={skillNames} personNames={personNames} />);
  expect(await screen.findByText("Esta execução não tem alternativas viáveis para detalhar.")).toBeInTheDocument();
  cleanup();

  stubPlans({ detail: { code: "SNAPSHOT_NOT_FOUND" } }, false);
  render(<OperationalPlanPanel runs={runs} skillNames={skillNames} personNames={personNames} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("SNAPSHOT_NOT_FOUND");
});
