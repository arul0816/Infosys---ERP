import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/api";

export default function AdminDashboard() {
  const [summary, setSummary] = useState(null);
  const [users, setUsers] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [auditLoading, setAuditLoading] = useState(false);
  const [userSearch, setUserSearch] = useState("");
  const [userRoleFilter, setUserRoleFilter] = useState("");
  const [auditSearch, setAuditSearch] = useState("");
  const [auditTypeFilter, setAuditTypeFilter] = useState("All");
  const [msg, setMsg] = useState(null);

  const flash = (text, type = "success") => {
    setMsg({ text, type });
    setTimeout(() => setMsg(null), 4000);
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [sum, userList, logs] = await Promise.all([
        api.getAnalyticsSummary("30"),
        api.getUsers(),
        api.getAuditLogs("limit=100").catch(() => []),
      ]);
      setSummary(sum);
      setUsers(userList);
      setAuditLogs(logs);
    } catch (err) {
      flash(err.message || "Failed to load admin dashboard data.", "error");
    } finally {
      setLoading(false);
    }
  };

  const loadAuditLogs = async () => {
    setAuditLoading(true);
    try {
      const params = new URLSearchParams();
      if (auditTypeFilter && auditTypeFilter !== "All") params.append("object_type", auditTypeFilter);
      if (auditSearch) params.append("search", auditSearch);
      params.append("limit", "100");
      const logs = await api.getAuditLogs(params.toString());
      setAuditLogs(logs);
    } catch (err) {
      flash(err.message || "Failed to refresh audit logs.", "error");
    } finally {
      setAuditLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRoleChange = async (userId, newRole) => {
    try {
      await api.updateUserRole(userId, newRole);
      flash(`User role successfully changed to ${newRole}`);
      loadData();
    } catch (err) {
      flash(err.message || "Failed to change role", "error");
    }
  };

  const handleStatusToggle = async (userId, currentStatus) => {
    const nextStatus = currentStatus === "active" ? "inactive" : "active";
    try {
      await api.updateUserStatus(userId, nextStatus);
      flash(`User account status updated to ${nextStatus}`);
      loadData();
    } catch (err) {
      flash(err.message || "Failed to update user status", "error");
    }
  };

  const handleDeleteUser = async (userId, userName) => {
    if (!confirm(`Delete user account '${userName}' permanently?`)) return;
    try {
      await api.deleteUser(userId);
      flash("User deleted successfully.");
      loadData();
    } catch (err) {
      flash(err.message || "Failed to delete user", "error");
    }
  };

  const filteredUsers = users.filter((u) => {
    const matchSearch =
      u.name.toLowerCase().includes(userSearch.toLowerCase()) ||
      u.email.toLowerCase().includes(userSearch.toLowerCase()) ||
      (u.organization && u.organization.toLowerCase().includes(userSearch.toLowerCase()));
    const matchRole = !userRoleFilter || u.role === userRoleFilter;
    return matchSearch && matchRole;
  });

  const filteredAuditLogs = auditLogs.filter((log) => {
    const matchType = auditTypeFilter === "All" || log.object_type?.toLowerCase() === auditTypeFilter.toLowerCase();
    const searchLower = auditSearch.toLowerCase();
    const matchSearch =
      !auditSearch ||
      log.actor_name?.toLowerCase().includes(searchLower) ||
      log.action?.toLowerCase().includes(searchLower) ||
      log.object_label?.toLowerCase().includes(searchLower) ||
      log.previous_value?.toLowerCase().includes(searchLower) ||
      log.new_value?.toLowerCase().includes(searchLower);
    return matchType && matchSearch;
  });

  const formatDiff = (prev, next) => {
    if (!prev && !next) return "—";
    if (!prev && next) return <span style={{ color: "#059669" }}>+ {typeof next === "object" ? JSON.stringify(next) : String(next)}</span>;
    if (prev && !next) return <span style={{ color: "#dc2626" }}>- {typeof prev === "object" ? JSON.stringify(prev) : String(prev)}</span>;
    return (
      <span style={{ fontSize: "0.85rem" }}>
        <del style={{ color: "#94a3b8", marginRight: "0.3rem" }}>{typeof prev === "object" ? JSON.stringify(prev) : String(prev)}</del>
        <span style={{ color: "#2563eb", fontWeight: "bold" }}>➔ {typeof next === "object" ? JSON.stringify(next) : String(next)}</span>
      </span>
    );
  };

  if (loading && !summary) {
    return (
      <div className="loading-state">
        <div className="spinner"></div>
        <p>Loading administrator workspace...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h1>🛡️ Administrator Control Center</h1>
            <p>System governance, user role administration, platform telemetry and enterprise audit logging</p>
          </div>
          <div className="btn-row" style={{ margin: 0 }}>
            <Link to="/analytics" className="btn btn-primary">
              📈 Open Deep Analytics
            </Link>
            <Link to="/events" className="btn btn-outline">
              📅 Manage All Events
            </Link>
          </div>
        </div>
      </div>

      {msg && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}

      {/* KPI Metric Cards */}
      {summary && (
        <div className="stat-row">
          <div className="stat-card">
            <div className="stat-value">{users.length}</div>
            <div className="stat-label">Total Users</div>
          </div>
          <div className="stat-card" style={{ background: "#4338ca" }}>
            <div className="stat-value">{summary.total_events}</div>
            <div className="stat-label">Total Events</div>
          </div>
          <div className="stat-card" style={{ background: "#059669" }}>
            <div className="stat-value">{summary.total_registrations}</div>
            <div className="stat-label">Total Registrations</div>
          </div>
          <div className="stat-card" style={{ background: "#d97706" }}>
            <div className="stat-value">{summary.attendance_rate}%</div>
            <div className="stat-label">Overall Attendance Rate</div>
          </div>
          <div className="stat-card" style={{ background: "#7c3aed" }}>
            <div className="stat-value">₹{Number(summary.total_budget).toLocaleString()}</div>
            <div className="stat-label">Allocated Budget</div>
          </div>
        </div>
      )}

      {/* User Management Section */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.75rem" }}>
          <h2>User Role & Account Management ({filteredUsers.length})</h2>

          <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
            <div className="form-group" style={{ margin: 0, minWidth: "220px" }}>
              <input
                type="text"
                placeholder="Search user by name, email or org..."
                value={userSearch}
                onChange={(e) => setUserSearch(e.target.value)}
              />
            </div>
            <div className="form-group" style={{ margin: 0, minWidth: "150px" }}>
              <select value={userRoleFilter} onChange={(e) => setUserRoleFilter(e.target.value)}>
                <option value="">All Roles</option>
                <option value="admin">Admins</option>
                <option value="organizer">Organizers</option>
                <option value="participant">Participants</option>
              </select>
            </div>
          </div>
        </div>

        {filteredUsers.length === 0 ? (
          <p className="empty-state">No users match the search criteria.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>User</th>
                  <th>Email</th>
                  <th>Organization</th>
                  <th>Current Role</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((u) => (
                  <tr key={u.id}>
                    <td>
                      <strong>{u.name}</strong>
                    </td>
                    <td>{u.email}</td>
                    <td>{u.organization || "—"}</td>
                    <td>
                      <select
                        value={u.role}
                        onChange={(e) => handleRoleChange(u.id, e.target.value)}
                        className="role-selector-select"
                      >
                        <option value="participant">Participant</option>
                        <option value="organizer">Organizer</option>
                        <option value="admin">Administrator</option>
                      </select>
                    </td>
                    <td>
                      <span className={`badge badge-${u.status === "active" ? "available" : "unavailable"}`}>
                        {u.status}
                      </span>
                    </td>
                    <td>
                      <div className="btn-row" style={{ margin: 0 }}>
                        <button
                          className={`btn btn-sm ${u.status === "active" ? "btn-warning" : "btn-success"}`}
                          onClick={() => handleStatusToggle(u.id, u.status)}
                        >
                          {u.status === "active" ? "Deactivate" : "Activate"}
                        </button>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => handleDeleteUser(u.id, u.name)}
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Enterprise Audit Log Explorer */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.75rem" }}>
          <div>
            <h2>📜 Enterprise Audit Log Explorer ({filteredAuditLogs.length})</h2>
            <p style={{ fontSize: "0.85rem", color: "#64748b", margin: 0 }}>
              Immutable audit trail tracking governance actions, role adjustments, status changes, and critical operations
            </p>
          </div>

          <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
            <div className="form-group" style={{ margin: 0, minWidth: "220px" }}>
              <input
                type="text"
                placeholder="Search actor, object, action, diff..."
                value={auditSearch}
                onChange={(e) => setAuditSearch(e.target.value)}
              />
            </div>
            <div className="form-group" style={{ margin: 0, minWidth: "150px" }}>
              <select value={auditTypeFilter} onChange={(e) => setAuditTypeFilter(e.target.value)}>
                <option value="All">All Object Types</option>
                <option value="event">Event Actions</option>
                <option value="user">User Actions</option>
                <option value="attendee">Attendee & Registrations</option>
                <option value="resource">Resources</option>
                <option value="venue">Venues</option>
              </select>
            </div>
            <button className="btn btn-outline btn-sm" onClick={loadAuditLogs} disabled={auditLoading}>
              {auditLoading ? "Refreshing..." : "🔄 Refresh"}
            </button>
          </div>
        </div>

        {filteredAuditLogs.length === 0 ? (
          <p className="empty-state">No audit log entries recorded yet.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Actor (Who)</th>
                  <th>Action</th>
                  <th>Object</th>
                  <th>Target Details / Diff</th>
                </tr>
              </thead>
              <tbody>
                {filteredAuditLogs.map((log) => (
                  <tr key={log.id}>
                    <td style={{ whiteSpace: "nowrap", fontSize: "0.85rem", color: "#64748b" }}>
                      {log.created_at}
                    </td>
                    <td>
                      <div>
                        <strong>{log.actor_name || "System"}</strong>
                        <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                          <span className={`badge badge-sm badge-${log.actor_role === "admin" ? "active" : "draft"}`}>
                            {log.actor_role || "system"}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span className="badge badge-outline" style={{ fontFamily: "monospace", fontSize: "0.8rem" }}>
                        {log.action}
                      </span>
                    </td>
                    <td>
                      <div>
                        <span style={{ fontSize: "0.8rem", textTransform: "uppercase", fontWeight: 600, color: "#4f46e5" }}>
                          {log.object_type}
                        </span>
                        <div style={{ fontWeight: 500 }}>{log.object_label || `#${log.object_id}`}</div>
                      </div>
                    </td>
                    <td>
                      {formatDiff(log.previous_value, log.new_value)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* System Quick Links */}
      <div className="card">
        <h2>System Shortcuts & Data Exports</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
          <div className="shortcut-box">
            <h4>📊 Analytics Engine</h4>
            <p>View time-series conversions, category breakdowns, and top events.</p>
            <Link to="/analytics" className="btn btn-outline btn-sm">Launch Analytics</Link>
          </div>
          <div className="shortcut-box">
            <h4>📋 Master Event Report</h4>
            <p>Generate aggregated event summaries and export CSV datasets.</p>
            <Link to="/report" className="btn btn-outline btn-sm">Open Reports</Link>
          </div>
          <div className="shortcut-box">
            <h4>📷 Check-In Scanner</h4>
            <p>Open live camera and token QR check-in terminal.</p>
            <Link to="/attendance" className="btn btn-outline btn-sm">Launch Scanner</Link>
          </div>
        </div>
      </div>
    </div>
  );
}

