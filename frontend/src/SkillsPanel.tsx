import { useEffect, useState } from "react";

import { createSkill, fetchSkills, updateSkill, type CatalogSkill } from "./api";
import { Pager, usePagination } from "./Pagination";

function friendlyError(caught: unknown): string {
  const code = caught instanceof Error ? caught.message : "Erro de conexão";
  const messages: Record<string, string> = {
    AUTHENTICATION_REQUIRED: "Acesso não autenticado. Entre novamente.",
    FORBIDDEN: "Seu perfil pode consultar, mas não cadastrar skills.",
    REQUIRED_SKILL_NAME: "Informe o nome da skill.",
    SKILL_ALREADY_EXISTS: "Essa skill já existe no catálogo.",
    SKILL_NOT_FOUND: "A skill não existe mais; atualize a lista.",
  };
  return messages[code] ?? code;
}

export default function SkillsPanel() {
  const [skills, setSkills] = useState<CatalogSkill[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const pages = usePagination(skills);

  async function load() {
    setBusy(true);
    setError(null);
    try {
      const loaded = await fetchSkills();
      setSkills(Array.isArray(loaded) ? loaded : []);
    } catch (caught) {
      setError(friendlyError(caught));
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => { void load(); }, []);

  function cancelEdit() {
    setEditingId(null);
    setName("");
    setDescription("");
  }

  function startEditing(skill: CatalogSkill) {
    setEditingId(skill.skill_id);
    setName(skill.skill_name);
    setDescription(skill.description ?? "");
    setMessage(null);
    setError(null);
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const skill = editingId
        ? await updateSkill(editingId, name.trim(), description.trim() || undefined)
        : await createSkill(name.trim(), description.trim() || undefined);
      setSkills((current) => [...current.filter((item) => item.skill_id !== skill.skill_id), skill]
        .sort((first, second) => first.skill_name.localeCompare(second.skill_name)));
      setMessage(`Skill ${skill.skill_name} ${editingId ? "atualizada" : "cadastrada"}.`);
      cancelEdit();
    } catch (caught) {
      setError(friendlyError(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="skills-section" aria-labelledby="skills-catalog-heading">
      <div className="section-heading"><div><p className="eyebrow">SKILLS</p><h2 id="skills-catalog-heading">Catálogo de skills</h2></div><span className="row-count">{skills.length} skills</span></div>
      {error && <p className="competency-error" role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
      <form className="competency-lookup" onSubmit={submit}>
        <label htmlFor="skills-new-name">{editingId ? "Nome da skill" : "Nova skill"}<input id="skills-new-name" value={name} disabled={busy} onChange={(event) => setName(event.target.value)} required maxLength={150} /></label>
        <label htmlFor="skills-new-description">Descrição<input id="skills-new-description" value={description} disabled={busy} onChange={(event) => setDescription(event.target.value)} maxLength={1000} /></label>
        <button type="submit" disabled={busy || !name.trim()}>{editingId ? "Salvar alterações" : "Cadastrar skill"}</button>
        {editingId && <button type="button" disabled={busy} onClick={cancelEdit}>Cancelar edição</button>}
      </form>
      <div className="table-scroll" role="region" aria-label="Skills cadastradas" tabIndex={0}>
        <table><caption className="visually-hidden">Skills cadastradas no catálogo</caption>
          <thead><tr><th scope="col">Skill</th><th scope="col">Descrição</th><th scope="col">Ação</th></tr></thead>
          <tbody>
            {pages.visible.map((skill) => <tr key={skill.skill_id}><th scope="row">{skill.skill_name}</th><td>{skill.description ?? "—"}</td><td><button type="button" disabled={busy} onClick={() => startEditing(skill)} aria-label={`Editar ${skill.skill_name}`}>Editar</button></td></tr>)}
            {skills.length === 0 && <tr><td colSpan={3}>{busy ? "Carregando…" : "Nenhuma skill cadastrada."}</td></tr>}
          </tbody>
        </table>
      </div>
      <Pager pagination={pages} label="skills" />
    </section>
  );
}
