import { useState } from "react";

import { createPerson, createSkill, fetchPeople, fetchSkills, type CatalogPerson, type CatalogSkill } from "./api";

type CatalogSetupProps = {
  loaded: boolean;
  onLoaded: (people: CatalogPerson[], skills: CatalogSkill[]) => void;
  onPersonCreated: (person: CatalogPerson) => void;
  onSkillCreated: (skill: CatalogSkill) => void;
};

function friendlyError(caught: unknown): string {
  const code = caught instanceof Error ? caught.message : "Erro de conexão";
  const messages: Record<string, string> = {
    AUTHENTICATION_REQUIRED: "Acesso não autenticado. Verifique a configuração do servidor.",
    FORBIDDEN: "Seu perfil pode consultar, mas não cadastrar pessoas ou skills.",
    REQUIRED_DISPLAY_NAME: "Informe o nome da pessoa.",
    REQUIRED_SKILL_NAME: "Informe o nome da skill.",
    SKILL_ALREADY_EXISTS: "Essa skill já existe no catálogo.",
  };
  return messages[code] ?? code;
}

export default function CatalogSetup({ loaded, onLoaded, onPersonCreated, onSkillCreated }: CatalogSetupProps) {
  const [personName, setPersonName] = useState("");
  const [skillName, setSkillName] = useState("");
  const [skillDescription, setSkillDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function loadCatalogs() {
    setBusy(true);
    setError(null);
    try {
      const [people, skills] = await Promise.all([fetchPeople(), fetchSkills()]);
      onLoaded(people, skills);
      setMessage("Catálogo carregado.");
    } catch (caught) {
      setError(friendlyError(caught));
    } finally {
      setBusy(false);
    }
  }

  async function submitPerson(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const person = await createPerson(personName.trim());
      onPersonCreated(person);
      setPersonName("");
      setMessage(`Pessoa ${person.display_name} cadastrada e selecionada.`);
    } catch (caught) {
      setError(friendlyError(caught));
    } finally {
      setBusy(false);
    }
  }

  async function submitSkill(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const skill = await createSkill(skillName.trim(), skillDescription.trim() || undefined);
      onSkillCreated(skill);
      setSkillName("");
      setSkillDescription("");
      setMessage(`Skill ${skill.skill_name} cadastrada e selecionada.`);
    } catch (caught) {
      setError(friendlyError(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="catalog-setup">
      {!loaded ? (
        <button type="button" disabled={busy} onClick={() => void loadCatalogs()}>
          {busy ? "Carregando catálogo…" : "Carregar pessoas e skills"}
        </button>
      ) : (
        <div className="catalog-forms">
          <form className="competency-lookup" onSubmit={submitPerson}>
            <label htmlFor="new-person-name">Nova pessoa<input id="new-person-name" value={personName} disabled={busy} onChange={(event) => setPersonName(event.target.value)} required maxLength={200} /></label>
            <button type="submit" disabled={busy || !personName.trim()}>Cadastrar pessoa</button>
          </form>
          <form className="competency-lookup" onSubmit={submitSkill}>
            <label htmlFor="new-skill-name">Nova skill<input id="new-skill-name" value={skillName} disabled={busy} onChange={(event) => setSkillName(event.target.value)} required maxLength={150} /></label>
            <label htmlFor="new-skill-description">Descrição<input id="new-skill-description" value={skillDescription} disabled={busy} onChange={(event) => setSkillDescription(event.target.value)} maxLength={1000} /></label>
            <button type="submit" disabled={busy || !skillName.trim()}>Cadastrar skill</button>
          </form>
          <button type="button" disabled={busy} onClick={() => void loadCatalogs()}>Atualizar catálogo</button>
        </div>
      )}
      {error && <p className="competency-error" role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
    </div>
  );
}
