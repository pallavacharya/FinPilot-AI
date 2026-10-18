import { useState } from "react";
import { useRouter } from "next/router";
import { login } from "../lib/api";
import Logo from "../components/Logo";

export default function Login() {
  const [email, setEmail] = useState("owner@aaravretail.com");
  const [password, setPassword] = useState("demo1234");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError("Invalid email or password.");
    } finally {
      setLoading(false);
    }
  }

  function quickFill(role) {
    if (role === "owner") {
      setEmail("owner@aaravretail.com");
      setPassword("demo1234");
    } else {
      setEmail("analyst@aaravretail.com");
      setPassword("demo1234");
    }
  }

  return (
    <div className="login-shell">
      <div className="login-card">
        <div className="brand">
          <Logo />
        </div>
        <h1>Sign in</h1>
        <p className="sub">Role-based access — enforced by the FastAPI backend via JWT.</p>

        <form onSubmit={handleSubmit}>
          <label className="field-label">Email</label>
          <input
            className="field"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
          />
          <label className="field-label">Password</label>
          <input
            className="field"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
          <button className="btn primary" type="submit" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </button>
          {error && <div className="err">{error}</div>}
        </form>

        <div className="demo-hint">
          Demo accounts — click to fill:
          <br />
          <span style={{ cursor: "pointer" }} onClick={() => quickFill("owner")}>
            <code>owner@aaravretail.com</code> (Owner, full access)
          </span>
          <br />
          <span style={{ cursor: "pointer" }} onClick={() => quickFill("analyst")}>
            <code>analyst@aaravretail.com</code> (Analyst, review + approve)
          </span>
          <br />
          password for both: <code>demo1234</code>
        </div>
      </div>
    </div>
  );
}
