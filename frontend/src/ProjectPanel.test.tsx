import { afterEach, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import ProjectPanel from "./ProjectPanel";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("loads project/skill catalogs and records a demand for the selected project", async () => {
  const user = userEvent.setup();
  const project = {
    project_id: "PRJ-001", project_name: "Atlas", horizon_start: "2026-01-01",
    horizon_end: "2026-12-01", load_unit: "hours",
  };
  const demand = {
    demand_id: "D-001", project_id: "PRJ-001", skill_id: "SKILL-1",
    proficiency_level: 3, period: "2026-11", load_amount: 10, load_unit: "hours", actor_id: "A0091250",
  };
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const body = url === "/api/projects" ? [project]
      : url === "/api/skills" ? [{ skill_id: "SKILL-1", skill_name: "Python", description: null }]
        : url.endsWith("/demands") && init?.method === "POST" ? demand
          : url.endsWith("/demands") ? [] : project;
    return { ok: true, status: 200, json: async () => body };
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<ProjectPanel />);

  await user.click(screen.getByRole("button", { name: "Carregar projetos e skills" }));
  expect(await screen.findByRole("option", { name: /Atlas/ })).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("Skill demandada"), "SKILL-1");
  await user.clear(screen.getByLabelText("Período"));
  await user.type(screen.getByLabelText("Período"), "2026-11");
  await user.type(screen.getByLabelText("Carga"), "10");
  await user.click(screen.getByRole("button", { name: "Registrar demanda" }));

  const postCall = fetchMock.mock.calls.find(([url, init]) => String(url).endsWith("/demands") && init?.method === "POST");
  expect(postCall?.[0]).toBe("/api/projects/PRJ-001/demands");
  expect(JSON.parse(String(postCall?.[1]?.body))).toEqual({
    skill_id: "SKILL-1", proficiency_level: 3, period: "2026-11", load_amount: 10, load_unit: "hours",
  });
  expect(await screen.findByRole("row", { name: /D-001 Python 3 2026-11 10 hours/ })).toBeInTheDocument();
});

it("creates a project with monthly horizon and selects it", async () => {
  const user = userEvent.setup();
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const body = url === "/api/projects" && init?.method === "POST"
      ? { project_id: "PRJ-002", project_name: "Atlas", horizon_start: "2026-01-01", horizon_end: "2026-12-01", load_unit: "hours" }
      : url === "/api/projects" ? [] : url === "/api/skills" ? [] : [];
    return { ok: true, json: async () => body };
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<ProjectPanel />);
  await user.type(screen.getByLabelText("Nome do projeto"), "Atlas");
  await user.type(screen.getByLabelText("Início do horizonte"), "2026-01");
  await user.type(screen.getByLabelText("Fim do horizonte"), "2026-12");
  await user.click(screen.getByRole("button", { name: "Criar projeto" }));

  const postCall = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
  expect(postCall?.[0]).toBe("/api/projects");
  expect(JSON.parse(String(postCall?.[1]?.body))).toEqual({
    project_name: "Atlas", horizon_start: "2026-01-01", horizon_end: "2026-12-01", load_unit: "hours",
  });
  expect(await screen.findByRole("option", { name: /Atlas/ })).toBeInTheDocument();
});

it("loads the demand list when the selected project changes", async () => {
  const user = userEvent.setup();
  const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    const body = url === "/api/projects" ? [
      { project_id: "PRJ-001", project_name: "Atlas", horizon_start: "2026-01-01", horizon_end: "2026-12-01", load_unit: "hours" },
      { project_id: "PRJ-002", project_name: "Orion", horizon_start: "2026-06-01", horizon_end: "2026-12-01", load_unit: "hours" },
    ] : url === "/api/skills" ? []
      : url === "/api/projects/PRJ-002/demands" ? [{ demand_id: "D-002", project_id: "PRJ-002", skill_id: "SKILL-2", proficiency_level: 5, period: "2026-07", load_amount: 12, load_unit: "hours", actor_id: "A0091250" }]
        : [];
    return { ok: true, json: async () => body };
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<ProjectPanel />);

  await user.click(screen.getByRole("button", { name: "Carregar projetos e skills" }));
  await user.selectOptions(screen.getByLabelText("Projeto"), "PRJ-002");

  expect(await screen.findByRole("row", { name: /D-002 SKILL-2 5 2026-07 12 hours/ })).toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledWith("/api/projects/PRJ-002/demands", expect.objectContaining({ method: "GET" }));
});

it("shows a duplicate project error without adding a selection", async () => {
  const user = userEvent.setup();
  vi.stubGlobal("fetch", vi.fn(async () => ({
    ok: false,
    json: async () => ({ detail: { code: "PROJECT_ALREADY_EXISTS" } }),
  })));
  render(<ProjectPanel />);

  await user.type(screen.getByLabelText("Nome do projeto"), "Atlas");
  await user.type(screen.getByLabelText("Início do horizonte"), "2026-01");
  await user.type(screen.getByLabelText("Fim do horizonte"), "2026-12");
  await user.click(screen.getByRole("button", { name: "Criar projeto" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Já existe um projeto");
  expect(screen.queryByRole("option", { name: /Atlas/ })).not.toBeInTheDocument();
});

it("shows a permission error and does not add a demand row for a viewer", async () => {
  const user = userEvent.setup();
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/projects") {
      return { ok: true, json: async () => [{ project_id: "PRJ-001", project_name: "Atlas", horizon_start: "2026-01-01", horizon_end: "2026-12-01", load_unit: "hours" }] };
    }
    if (url === "/api/skills") {
      return { ok: true, json: async () => [{ skill_id: "SKILL-1", skill_name: "Python", description: null }] };
    }
    if (url.endsWith("/demands") && init?.method === "POST") {
      return { ok: false, status: 403, json: async () => ({ detail: { code: "FORBIDDEN" } }) };
    }
    return { ok: true, json: async () => [] };
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<ProjectPanel />);

  await user.click(screen.getByRole("button", { name: "Carregar projetos e skills" }));
  await user.selectOptions(screen.getByLabelText("Skill demandada"), "SKILL-1");
  await user.clear(screen.getByLabelText("Período"));
  await user.type(screen.getByLabelText("Período"), "2026-11");
  await user.type(screen.getByLabelText("Carga"), "10");
  await user.click(screen.getByRole("button", { name: "Registrar demanda" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Seu perfil pode consultar, mas não cadastrar");
  expect(screen.queryByRole("row", { name: /D-403/ })).not.toBeInTheDocument();
});