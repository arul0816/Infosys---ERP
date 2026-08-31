import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { api } from "../api/api";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || "/explore";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await api.login({ email: email.trim().toLowerCase(), password });
      login(res.user, res.token);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || "Failed to sign in. Please verify your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const quickDemoLogin = async (emailToUse, passwordToUse, role = "participant", name = "Demo User") => {
    setError(null);
    setLoading(true);
    setEmail(emailToUse);
    setPassword(passwordToUse);
    try {
      let res;
      try {
        res = await api.login({ email: emailToUse, password: passwordToUse });
      } catch (loginErr) {
        if (loginErr.message?.includes("Invalid email or password")) {
          await api.registerUser({
            name,
            email: emailToUse,
            password: passwordToUse,
            role,
            phone: "9876543210",
            organization: "EventSphere",
          });
          res = await api.login({ email: emailToUse, password: passwordToUse });
        } else {
          throw loginErr;
        }
      }
      login(res.user, res.token);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message || "Demo login failed. Make sure backend server is running.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page-wrap">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-icon-badge">🔐</div>
          <h2>Welcome Back</h2>
          <p>Sign in to your EventSphere account to manage or register for events</p>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label>Email Address</label>
            <input
              type="email"
              required
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          <div className="form-group">
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <label>Password</label>
            </div>
            <input
              type="password"
              required
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
            {loading ? "Signing In..." : "Sign In to Account"}
          </button>
        </form>

        <div className="demo-accounts-box">
          <span>⚡ 1-Click Demo Accounts</span>
          <div className="demo-btns-grid" style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginTop: "0.5rem" }}>
            <button
              type="button"
              className="demo-badge-btn badge-admin"
              onClick={() => quickDemoLogin("admin@eventsphere.com", "admin123", "admin", "Demo Admin")}
              disabled={loading}
            >
              🛡️ Sign in as Admin (admin@eventsphere.com)
            </button>
            <button
              type="button"
              className="demo-badge-btn badge-organizer"
              onClick={() => quickDemoLogin("organizer@eventsphere.com", "organizer123", "organizer", "Lead Organizer")}
              disabled={loading}
            >
              📊 Sign in as Organizer (organizer@eventsphere.com)
            </button>
            <button
              type="button"
              className="demo-badge-btn badge-participant"
              onClick={() => quickDemoLogin("user@eventsphere.com", "user123", "participant", "Active Participant")}
              disabled={loading}
            >
              👤 Sign in as Participant (user@eventsphere.com)
            </button>
          </div>
        </div>

        <div className="auth-footer">
          <p>
            Don't have an account? <Link to="/register">Register here</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
