import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ProtectedRoute({ children, allowedRoles }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", minHeight: "50vh" }}>
        <div className="spinner"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return (
      <div className="card" style={{ textAlign: "center", padding: "3rem 1.5rem", maxWidth: "600px", margin: "2rem auto" }}>
        <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>🔒</div>
        <h2>Access Restricted</h2>
        <p style={{ color: "#64748b", margin: "1rem 0" }}>
          You do not have permission to view this page. This area requires <strong>{allowedRoles.join(" or ")}</strong> privileges.
        </p>
        <a href="/" className="btn btn-primary" style={{ display: "inline-block", textDecoration: "none" }}>
          Return to Events
        </a>
      </div>
    );
  }

  return children;
}
