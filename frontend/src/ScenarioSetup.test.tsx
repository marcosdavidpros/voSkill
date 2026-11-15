import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ScenarioSetup from "./ScenarioSetup";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("selects a project and participant, records monthly availability and saves a base scenario", async () => {
  const user = userEvent.setup();
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const body = url === "/api/projects" ? [{ project_id: "PRJ-001", project_name: "Atlas", horizon_start: "2026-01-01", horizon_end: "2026-12-01", load_unit: "hours" }]
      : url === "/api/people" ? [{ person_id: "P-001", display_name: "Alex" }]
        : url.endsWith("/demands") ? [{ demand_id: "D-001", skill_id: "SKILL-1", proficiency_level: 3, period: "2026-01", load_amount: 10, load_unit: "hours", actor_id: "A0091250" }]
          : { scenario_id: "SCN-001", snapshot_id: "SNP-001", project_id: "PRJ-001", scenario_name: "Baseline", scenario_type: "BASE" };
    return { ok: true, json: async () => body };
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<ScenarioSetup onCreated={vi.fn()} />);

  await user.click(screen.getByRole("button", { name: "Carregar projetos e pessoas" }));
  await user.selectOptions(screen.getByLabelText("Projeto"), "PRJ-001");
  await user.type(screen.getByLabelText("Nome do cenário-base"), "Baseline");
  await user.click(screen.getByRole("checkbox", { name: "P-001 · Alex" }));
  await user.clear(screen.getByLabelText("Disponibilidade P-001 em 2026-01 (horas)"));
  await user.type(screen.getByLabelText("Disponibilidade P-001 em 2026-01 (horas)"), "40");
  await user.click(screen.getByRole("button", { name: "Salvar cenário-base" }));

  const postCall = fetchMock.mock.calls.find(([url, init]) => String(url).endsWith("/scenarios") && init?.method === "POST");
  expect(postCall?.[0]).toBe("/api/projects/PRJ-001/scenarios");
  expect(JSON.parse(String(postCall?.[1]?.body))).toEqual({
    scenario_name: "Baseline",
    participants: [{ person_id: "P-001", availability: { "2026-01": 40 } }],
  });
  expect(await screen.findByText(/SCN-001.*SNP-001/)).toBeInTheDocument();
});

it("shows unauthorized errors without selecting a scenario", async () => {
  const user = userEvent.setup();
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: false,
    status: 403,
    json: async () => ({ detail: { code: "FORBIDDEN" } }),
  })));
  render(<ScenarioSetup onCreated={vi.fn()} />);
  await user.click(screen.getByRole("button", { name: "Carregar projetos e pessoas" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("não pode criar cenários");
  expect(screen.queryByText(/SCN-/)).not.toBeInTheDocument();
});
