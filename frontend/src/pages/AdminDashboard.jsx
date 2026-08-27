import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/api";

export default function AdminDashboard() {
  const [summary, setSummary] = useState(null);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [userSearch, setUserSearch] = useState("");
  const [userRoleFilter, setUserRoleFilter] = useState("");
  const [msg, setMsg] = useState(null);

  const flash = (text, type = "success") => {
    setMsg({ text, type });
    setTimeout(() => setMsg(null), 4000);
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const [sum, userList] = await Promise.all([
        api.getAnalyticsSummary("30"),
        api.getUsers(),
      ]);
      setSummary(sum);
      setUsers(userList);
    } catch (err) {
      flash(err.message || "Failed to load admin dashboard data.", "error");
    } finally {
      setLoading(false);
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
            <p>System governance, user role administration, platform telemetry and data oversight</p>
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
