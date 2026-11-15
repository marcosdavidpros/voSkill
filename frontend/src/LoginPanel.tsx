import { useState } from "react";

type LoginPanelProps = {
  error: string | null;
  onLogin: (username: string, password: string) => Promise<void>;
};

const messages: Record<string, string> = {
  INVALID_CREDENTIALS: "Matrícula, senha ou permissão do voSkill inválida.",
  AUTHENTICATION_UNAVAILABLE: "Autenticação indisponível. Tente novamente mais tarde.",
};

export default function LoginPanel({ error, onLogin }: LoginPanelProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setLocalError(null);
    try {
      await onLogin(username.trim(), password);
    } catch (caught) {
      const code = caught instanceof Error ? caught.message : "AUTHENTICATION_UNAVAILABLE";
      setLocalError(messages[code] ?? "Não foi possível autenticar. Verifique a matrícula e tente novamente.");
    } finally {
      setPassword("");
      setBusy(false);
    }
  }

  return (
    <section className="login-panel" aria-labelledby="login-heading">
      <p className="eyebrow">ACESSO CORPORATIVO</p>
      <h1 id="login-heading">Entrar no voSkill</h1>
      <form onSubmit={submit}>
        <label htmlFor="login-username">Matrícula<input id="login-username" name="username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required disabled={busy} /></label>
        <label htmlFor="login-password">Senha<input id="login-password" name="password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required disabled={busy} /></label>
        {(localError || error) && <p role="alert">{localError ?? error}</p>}
        <button type="submit" disabled={busy || !username.trim() || !password}>{busy ? "Autenticando…" : "Entrar"}</button>
      </form>
    </section>
  );
}