import { useEffect, useState } from "react";

import type { CompetencyMap, RiskPanel as RiskPanelData } from "./api";

type RiskPanelProps = {
  competencyMap: CompetencyMap;
  panel: RiskPanelData | null;
  error: string | null;
  savedMessage: string | null;
  saving: boolean;
  onSave: (skillId: string, threshold: number) => Promise<void>;
};

export default function RiskPanel({
  competencyMap,
  panel,
  error,
  savedMessage,
  saving,
  onSave,
}: RiskPanelProps) {
  const [skillId, setSkillId] = useState(competencyMap.skills[0]?.skill_id ?? "");
  const [thresholdText, setThresholdText] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    setThresholdText(panel?.thresholds?.[skillId]?.toString() ?? "");
  }, [panel, skillId]);

  const threshold = Number(thresholdText);
  const canSave = Number.isInteger(threshold) && threshold >= 1 && skillId.length > 0;
  const risks = panel?.risks ?? [];
  const configuredThresholds = panel?.thresholds ?? {};

  async function submitThreshold(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSave) {
      setValidationError("Informe um limiar de pelo menos 1 pessoa.");
      return;
    }
    setValidationError(null);
    await onSave(skillId, threshold);
  }

  return (
    <section className="risk-section" aria-labelledby="risk-heading">
      <div className="section-heading">
        <div>
          <p className="eyebrow">DEPENDÊNCIA DE SKILLS</p>
          <h2 id="risk-heading">Risco por limiar configurado</h2>
        </div>
      </div>

      {error ? (
        <p className="risk-message" role="alert">Painel de risco indisponível: {error}</p>
      ) : !panel ? (
        <p className="risk-message" role="status">Carregando limiares e evidências…</p>
      ) : risks.length === 0 ? (
        <p className="risk-message" role="status">
          {Object.keys(configuredThresholds).length === 0
            ? "Nenhum limiar configurado."
            : "Nenhuma skill está abaixo do limiar configurado."}
        </p>
      ) : (
        <ul className="risk-list">
          {risks.map((risk) => (
            <li key={risk.skill_id}>
              <strong>{risk.skill_name}</strong>
              <span>
                {risk.confirmed_count} confirmado{risk.confirmed_count === 1 ? "" : "s"} de {risk.threshold} necessários
              </span>
              {risk.people.length > 0 && (
                <ul>
                  {risk.people.map((person) => (
                    <li key={person.person_id}>
                      {person.person_id} · {person.evidence}
                    </li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      )}

      <form className="risk-threshold-form" onSubmit={submitThreshold}>
        <label htmlFor="risk-skill">Skill crítica</label>
        <select
          id="risk-skill"
          value={skillId}
          onChange={(event) => setSkillId(event.target.value)}
          disabled={competencyMap.skills.length === 0}
        >
          {competencyMap.skills.map((skill) => (
            <option key={skill.skill_id} value={skill.skill_id}>
              {skill.holders.find((holder) => holder.skill_name)?.skill_name ?? skill.skill_id}
            </option>
          ))}
        </select>
        <label htmlFor="risk-threshold">Limiar de pessoas confirmadas</label>
        <input
          id="risk-threshold"
          type="number"
          min={1}
          step={1}
          value={thresholdText}
          onChange={(event) => setThresholdText(event.target.value)}
        />
        <button type="submit" disabled={saving || !canSave}>
          {saving ? "Salvando…" : "Salvar limiar"}
        </button>
      </form>
      {(validationError || savedMessage) && (
        <p className="risk-message" role="status">{validationError ?? savedMessage}</p>
      )}
    </section>
  );
}