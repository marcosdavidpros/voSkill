import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
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

  await screen.findByRole("option", { name: "Atlas" });
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
  expect(await screen.findByText(/Cenário "Baseline" salvo/)).toBeInTheDocument();
  expect(screen.queryByText(/SCN-001|SNP-001/)).not.toBeInTheDocument();
});

it("shows unauthorized errors without selecting a scenario", async () => {
  const user = userEvent.setup();
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: false,
    status: 403,
    json: async () => ({ detail: { code: "FORBIDDEN" } }),
  })));
  render(<ScenarioSetup onCreated={vi.fn()} />);
  expect(await screen.findByRole("alert")).toHaveTextContent("não pode criar cenários");
  expect(screen.queryByText(/SCN-/)).not.toBeInTheDocument();
});

it("applies one monthly workload to every month of a participant", async () => {
  const user = userEvent.setup();
  const demands = ["2026-06", "2026-07", "2026-08"].map((period, index) => ({
    demand_id: `D-00${index + 1}`, skill_id: "SKILL-1", proficiency_level: 3, period, load_amount: 10, load_unit: "hours", actor_id: "A0091250",
  }));
  const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
    const url = String(input);
    const body = url === "/api/projects" ? [{ project_id: "PRJ-001", project_name: "Atlas", horizon_start: "2026-01-01", horizon_end: "2026-12-01", load_unit: "hours" }]
      : url === "/api/people" ? [{ person_id: "P-004", display_name: "Davi" }]
        : url.endsWith("/demands") ? demands
          : { scenario_id: "SCN-007", snapshot_id: "SNP-007", project_id: "PRJ-001", scenario_name: "Q3", scenario_type: "BASE" };
    return { ok: true, json: async () => body };
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<ScenarioSetup onCreated={vi.fn()} />);

  await screen.findByRole("option", { name: "Atlas" });
  await user.selectOptions(screen.getByLabelText("Projeto"), "PRJ-001");
  await user.type(screen.getByLabelText("Nome do cenário-base"), "Q3");
  await user.click(screen.getByRole("checkbox", { name: "P-004 · Davi" }));
  await user.type(screen.getByLabelText(/Carga horária mensal P-004/), "160");
  await user.clear(screen.getByLabelText("Disponibilidade P-004 em 2026-08 (horas)"));
  await user.type(screen.getByLabelText("Disponibilidade P-004 em 2026-08 (horas)"), "100");
  await user.click(screen.getByRole("button", { name: "Salvar cenário-base" }));

  const postCall = fetchMock.mock.calls.find(([url, init]) => String(url).endsWith("/scenarios") && init?.method === "POST");
  expect(JSON.parse(String(postCall?.[1]?.body)).participants).toEqual([
    { person_id: "P-004", availability: { "2026-06": 160, "2026-07": 160, "2026-08": 100 } },
  ]);
});

it("loads an existing scenario of the project, lets the user edit it and saves with PUT", async () => {
  const user = userEvent.setup();
  const onCreated = vi.fn();
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const body = url === "/api/projects" ? [{ project_id: "PRJ-001", project_name: "Atlas", horizon_start: "2026-01-01", horizon_end: "2026-12-01", load_unit: "hours" }]
      : url === "/api/people" ? [{ person_id: "P-001", display_name: "Alex" }, { person_id: "P-002", display_name: "Bia" }]
        : url === "/api/scenarios" ? [{ scenario_id: "SCN-009", scenario_name: "Baseline", scenario_type: "BASE", project_id: "PRJ-001", project_name: "Atlas" }]
          : url === "/api/scenarios/SCN-009/optimization-snapshot" ? { snapshot_id: "SNP-9", profiles: [{ person_id: "P-001", competencies: {}, availability: { "2026-01": 40 } }], demands: [] }
            : url.endsWith("/demands") ? [{ demand_id: "D-001", skill_id: "SKILL-1", proficiency_level: 3, period: "2026-01", load_amount: 10, load_unit: "hours", actor_id: "A0091250" }]
              : init?.method === "PUT" ? { scenario_id: "SCN-009", snapshot_id: "SNP-10", project_id: "PRJ-001", scenario_name: "Baseline v2", scenario_type: "BASE" }
                : [];
    return { ok: true, json: async () => body };
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<ScenarioSetup onCreated={onCreated} />);

  await screen.findByRole("option", { name: "Atlas" });
  await user.selectOptions(screen.getByLabelText("Projeto"), "PRJ-001");
  await user.selectOptions(screen.getByLabelText("Cenário"), "SCN-009");

  await waitFor(() => expect(screen.getByLabelText("Nome do cenário-base")).toHaveValue("Baseline"));
  expect(screen.getByRole("checkbox", { name: "P-001 · Alex" })).toBeChecked();
  expect(screen.getByRole("checkbox", { name: "P-002 · Bia" })).not.toBeChecked();
  const hours = screen.getByLabelText("Disponibilidade P-001 em 2026-01 (horas)");
  expect(hours).toHaveValue(40);

  await user.clear(hours);
  await user.type(hours, "60");
  await user.click(screen.getByRole("checkbox", { name: "P-002 · Bia" }));
  await user.type(screen.getByLabelText("Disponibilidade P-002 em 2026-01 (horas)"), "20");
  await user.clear(screen.getByLabelText("Nome do cenário-base"));
  await user.type(screen.getByLabelText("Nome do cenário-base"), "Baseline v2");
  await user.click(screen.getByRole("button", { name: "Salvar alterações" }));

  const putCall = fetchMock.mock.calls.find(([, init]) => init?.method === "PUT");
  expect(putCall?.[0]).toBe("/api/scenarios/SCN-009");
  expect(JSON.parse(String(putCall?.[1]?.body))).toEqual({
    scenario_name: "Baseline v2",
    participants: [
      { person_id: "P-001", availability: { "2026-01": 60 } },
      { person_id: "P-002", availability: { "2026-01": 20 } },
    ],
  });
  expect(await screen.findByText(/Baseline v2" atualizado/)).toBeInTheDocument();
  expect(onCreated).toHaveBeenCalledWith("SCN-009");
});

it("explains project demands in a table with skill names", async () => {
  const user = userEvent.setup();
  const fetchMock = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
    const url = String(input);
    const body = url === "/api/projects" ? [{ project_id: "PRJ-001", project_name: "Atlas", horizon_start: "2026-01-01", horizon_end: "2026-12-01", load_unit: "hours" }]
      : url === "/api/people" ? [{ person_id: "P-001", display_name: "Alex" }]
        : url === "/api/skills" ? [{ skill_id: "HS-008", skill_name: "Python", description: null }]
          : [{ demand_id: "11c794d1-6112", skill_id: "HS-008", proficiency_level: 2, period: "2026-06", load_amount: 160, load_unit: "hours", actor_id: "A0091250" }];
    return { ok: true, json: async () => body };
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<ScenarioSetup onCreated={vi.fn()} />);

  await screen.findByRole("option", { name: "Atlas" });
  await user.selectOptions(screen.getByLabelText("Projeto"), "PRJ-001");

  expect(await screen.findByRole("heading", { name: "Demandas do projeto" })).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: "Python (HS-008)" })).toBeInTheDocument();
  expect(screen.getByRole("cell", { name: "160 h" })).toBeInTheDocument();
  expect(screen.queryByText(/11c794d1/)).not.toBeInTheDocument();
});

it("renders and submits one availability value per person and distinct month", async () => {
  const user = userEvent.setup();
  const demands = ["SKILL-1", "SKILL-2", "SKILL-3", "SKILL-4", "SKILL-5"].map((skill_id, index) => ({
    demand_id: `D-00${index + 1}`, skill_id, proficiency_level: 3, period: "2026-06", load_amount: 10, load_unit: "hours", actor_id: "A0091250",
  }));
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const body = url === "/api/projects" ? [{ project_id: "PRJ-001", project_name: "Atlas", horizon_start: "2026-01-01", horizon_end: "2026-12-01", load_unit: "hours" }]
      : url === "/api/people" ? [{ person_id: "P-008", display_name: "Giovanna" }]
        : url.endsWith("/demands") ? demands
          : { scenario_id: "SCN-006", snapshot_id: "SNP-006", project_id: "PRJ-001", scenario_name: "June", scenario_type: "BASE" };
    return { ok: true, json: async () => body };
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<ScenarioSetup onCreated={vi.fn()} />);

  await screen.findByRole("option", { name: "Atlas" });
  await user.selectOptions(screen.getByLabelText("Projeto"), "PRJ-001");
  await user.type(screen.getByLabelText("Nome do cenário-base"), "June");
  await user.click(screen.getByRole("checkbox", { name: "P-008 · Giovanna" }));
  const monthlyAvailability = screen.getAllByLabelText("Disponibilidade P-008 em 2026-06 (horas)");
  expect(monthlyAvailability).toHaveLength(1);
  await user.type(monthlyAvailability[0], "40");
  await user.click(screen.getByRole("button", { name: "Salvar cenário-base" }));

  const postCall = fetchMock.mock.calls.find(([url, init]) => String(url).endsWith("/scenarios") && init?.method === "POST");
  expect(JSON.parse(String(postCall?.[1]?.body))).toEqual({
    scenario_name: "June",
    participants: [{ person_id: "P-008", availability: { "2026-06": 40 } }],
  });
});
