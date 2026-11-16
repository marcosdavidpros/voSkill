import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import OptimizationPanel from "./OptimizationPanel";
import { Pager, usePagination } from "./Pagination";
import type { OptimizationRunSummary, ScenarioOption } from "./api";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function Sample({ count }: { count: number }) {
  const pages = usePagination(Array.from({ length: count }, (_, index) => `item-${index + 1}`));
  return <>
    <ul>{pages.visible.map((item) => <li key={item}>{item}</li>)}</ul>
    <Pager pagination={pages} label="itens" />
  </>;
}

describe("paginação de tabelas", () => {
  it("não mostra o paginador quando tudo cabe em uma página", () => {
    render(<Sample count={10} />);

    expect(screen.queryByRole("navigation", { name: /Paginação/ })).not.toBeInTheDocument();
    expect(screen.getAllByRole("listitem")).toHaveLength(10);
  });

  it("navega entre as páginas e desabilita os limites", async () => {
    const user = userEvent.setup();
    render(<Sample count={25} />);

    expect(screen.getAllByRole("listitem")).toHaveLength(10);
    expect(screen.getByText("Página 1 de 3 · 1–10 de 25")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Próxima" }));
    await user.click(screen.getByRole("button", { name: "Próxima" }));

    expect(screen.getAllByRole("listitem")).toHaveLength(5);
    expect(screen.getByText("item-25")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Próxima" })).toBeDisabled();
  });
});

describe("histórico de cálculos do cenário", () => {
  const scenarios: ScenarioOption[] = [
    { scenario_id: "S-1", scenario_name: "Equipe", scenario_type: "BASE", project_id: "P-1", project_name: "Atlas" },
  ];
  const run = (index: number, scenario = "Equipe"): OptimizationRunSummary => ({
    run_id: `RUN-${index}`,
    created_at: "2026-11-16T12:00:00Z",
    scenario_name: scenario,
    project_name: "Atlas",
    status: "feasible",
    seed: index,
    population_size: 20,
    generations: 12,
    rejected_count: 0,
    alternative_ids: ["A-001"],
  });

  it("lista só os cálculos do cenário selecionado, paginados", async () => {
    const user = userEvent.setup();
    const runs = [...Array.from({ length: 12 }, (_, index) => run(index + 1)), run(99, "Outro")];
    render(<OptimizationPanel scenarioId="S-1" scenarios={scenarios} runs={runs} onScenarioChange={() => undefined} onRunCreated={() => undefined} />);

    const history = screen.getByRole("region", { name: "Histórico de cálculos do cenário" });
    expect(history.querySelectorAll("tbody tr")).toHaveLength(10);
    expect(screen.getByText("12 cálculos")).toBeInTheDocument();
    expect(screen.queryByText("RUN-99")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Próxima" }));

    expect(history.querySelectorAll("tbody tr")).toHaveLength(2);
  });

  it("informa quando o cenário ainda não foi calculado", () => {
    render(<OptimizationPanel scenarioId="S-1" scenarios={scenarios} runs={[]} onScenarioChange={() => undefined} onRunCreated={() => undefined} />);

    expect(screen.getByText("Nenhum cálculo salvo para este cenário.")).toBeInTheDocument();
  });

  it("abre o detalhe de um cálculo com todas as alternativas, paginadas", async () => {
    const user = userEvent.setup();
    const alternatives = Array.from({ length: 51 }, (_, index) => ({
      alternative_id: `A-${String(index + 1).padStart(3, "0")}`,
      objective_metrics: { skill_gap_hours: index, peak_utilization: 1.5 },
    }));
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        run_id: "RUN-1",
        seed: 1,
        algorithm_version: "pymoo-0",
        result: {
          status: "feasible",
          feasible_alternatives: alternatives,
          rejected_alternatives: [],
          run_metadata: { snapshot_id: "SNP-1", algorithm: "NSGA-II", configuration: { population_size: 20, generations: 12, objectives: [] } },
        },
      }),
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<OptimizationPanel scenarioId="S-1" scenarios={scenarios} runs={[run(1)]} onScenarioChange={() => undefined} onRunCreated={() => undefined} />);

    await user.click(screen.getByRole("button", { name: "Ver detalhe da execução RUN-1" }));

    const detail = await screen.findByRole("region", { name: "Detalhe da execução RUN-1" });
    expect(fetchMock).toHaveBeenCalledWith("/api/optimization-runs/RUN-1", expect.objectContaining({ method: "GET" }));
    expect(detail.querySelectorAll("tbody tr")).toHaveLength(10);
    expect(screen.getByText("Página 1 de 6 · 1–10 de 51")).toBeInTheDocument();
  });
});
