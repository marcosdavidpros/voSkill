import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import OptimizationPanel from "./OptimizationPanel";

const scenarios = [
  { scenario_id: "SCN-001", scenario_name: "Baseline", scenario_type: "BASE", project_id: "PRJ-001", project_name: "Atlas" },
  { scenario_id: "SCN-002", scenario_name: "Q3", scenario_type: "BASE", project_id: "PRJ-001", project_name: "Atlas" },
];

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("runs NSGA-II from the selected base scenario and shows separate objectives", async () => {
  const user = userEvent.setup();
  const snapshot = {
    snapshot_id: "SNP-001",
    profiles: [{ person_id: "P-001", competencies: { "SKILL-1": 4 }, availability: { "2026-01": 40 } }],
    demands: [{ demand_id: "D-001", skill_id: "SKILL-1", proficiency_level: 3, period: "2026-01", load_amount: 10 }],
  };
  const run = {
    run_id: "RUN-001",
    seed: 42,
    algorithm_version: "pymoo-0.6.2",
    configuration: { population_size: 20, generations: 12 },
    result: {
      status: "feasible",
      feasible_alternatives: [
        { alternative_id: "A-001", objective_metrics: { skill_gap_hours: 0.1, peak_utilization: 0.25 } },
        { alternative_id: "A-002", objective_metrics: { skill_gap_hours: 0.2, peak_utilization: 0.15 } },
      ],
      rejected_alternatives: [],
      constraint_evaluation: { checked_hard_constraints: ["capacity_exceeded"], rejected_alternatives: [] },
      run_metadata: {
        snapshot_id: "SNP-001", algorithm: "NSGA-II",
        configuration: { population_size: 20, generations: 12, objectives: ["skill_gap_hours", "peak_utilization"] },
      },
    },
  };
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => ({
    ok: true,
    status: 201,
    json: async () => String(input).includes("optimization-snapshot") ? snapshot : run,
  }));
  vi.stubGlobal("fetch", fetchMock);
  const onRunCreated = vi.fn();
  render(<OptimizationPanel scenarioId="SCN-001" scenarios={scenarios} onScenarioChange={vi.fn()} onRunCreated={onRunCreated} />);

  await user.click(screen.getByRole("button", { name: "Executar otimização" }));

  const runCall = fetchMock.mock.calls.find(([url]) => String(url) === "/api/optimization-runs");
  expect(runCall?.[1]?.method).toBe("POST");
  expect(JSON.parse(String(runCall?.[1]?.body))).toEqual({ snapshot, seed: 42, population_size: 20, generations: 12 });
  expect(await screen.findByRole("region", { name: "Resultado da execução RUN-001" })).toBeInTheDocument();
  expect(onRunCreated).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("row", { name: /A-001/ })).toHaveTextContent("0.1");
  expect(screen.getByRole("row", { name: /A-002/ })).toHaveTextContent("0.15");
  expect(screen.queryByRole("button", { name: /Aplicar/ })).not.toBeInTheDocument();
});

it("shows infeasible status and recorded violations without invoking an LLM", async () => {
  const user = userEvent.setup();
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => ({
    ok: true,
    status: 201,
    json: async () => String(input).includes("optimization-snapshot")
      ? { snapshot_id: "SNP-001", profiles: [], demands: [] }
      : { run_id: "RUN-002", result: { status: "infeasible", feasible_alternatives: [], rejected_alternatives: [{ alternative_id: "A-003", violations: [{ code: "capacity_exceeded" }] }] } },
  })));
  render(<OptimizationPanel scenarioId="SCN-001" scenarios={scenarios} onScenarioChange={vi.fn()} onRunCreated={vi.fn()} />);
  await user.click(screen.getByRole("button", { name: "Executar otimização" }));

  expect(await screen.findByText(/Sem alternativas viáveis/)).toBeInTheDocument();
  expect(screen.getByText(/capacity_exceeded/)).toBeInTheDocument();
});

it("lets the user choose which scenario to calculate by name", async () => {
  const user = userEvent.setup();
  const onScenarioChange = vi.fn();
  render(<OptimizationPanel scenarioId="SCN-001" scenarios={scenarios} onScenarioChange={onScenarioChange} onRunCreated={vi.fn()} />);

  const select = screen.getByRole("combobox", { name: "Cenário a calcular" });
  expect(screen.getByRole("option", { name: "Atlas · Baseline" })).toBeInTheDocument();
  await user.selectOptions(select, "SCN-002");

  expect(onScenarioChange).toHaveBeenCalledWith("SCN-002");
  expect(screen.queryByText(/SCN-001/)).not.toBeInTheDocument();
});
