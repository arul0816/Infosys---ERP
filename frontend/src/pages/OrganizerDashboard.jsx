import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/api";
import { useAuth } from "../context/AuthContext";

export default function OrganizerDashboard() {
  const { user } = useAuth();
  const [events, setEvents] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const [evList, sum] = await Promise.all([
        api.getMyEvents(),
        api.getAnalyticsSummary("30"),
      ]);
      setEvents(evList);
      setSummary(sum);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const totalRegistered = events.reduce((acc, e) => acc + (e.registered_count || 0), 0);
  const totalAttended = events.reduce((acc, e) => acc + (e.attended_count || 0), 0);
  const totalWaitlisted = events.reduce((acc, e) => acc + (e.waitlisted_count || 0), 0);

  if (loading && !summary) {
    return (
      <div className="loading-state">
        <div className="spinner"></div>
        <p>Loading your organizer workspace...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h1>📊 Organizer Workspace</h1>
            <p>Welcome back, {user?.name}. Monitor your events, manage registrations and oversee check-ins.</p>
          </div>
          <div className="btn-row" style={{ margin: 0 }}>
            <Link to="/events" className="btn btn-primary">
              ➕ Create New Event
            </Link>
            <Link to="/attendance" className="btn btn-success">
              📷 Open Check-In
            </Link>
          </div>
        </div>
      </div>

      {/* Scoped Metric Row */}
      <div className="stat-row">
        <div className="stat-card">
          <div className="stat-value">{events.length}</div>
          <div className="stat-label">My Events</div>
        </div>
        <div className="stat-card" style={{ background: "#4338ca" }}>
          <div className="stat-value">{totalRegistered}</div>
          <div className="stat-label">Registered Attendees</div>
        </div>
        <div className="stat-card" style={{ background: "#059669" }}>
          <div className="stat-value">{totalAttended}</div>
          <div className="stat-label">Checked-In Attended</div>
        </div>
        <div className="stat-card" style={{ background: "#d97706" }}>
          <div className="stat-value">{totalWaitlisted}</div>
          <div className="stat-label">In Waitlist Queue</div>
        </div>
      </div>

      {/* Events Overview */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <h2>My Active Events & Capacity ({events.length})</h2>
          <Link to="/events" className="btn btn-outline btn-sm">Manage All Events</Link>
        </div>

        {events.length === 0 ? (
          <div className="empty-state">
            <p>You have not created any events yet.</p>
            <Link to="/events" className="btn btn-primary" style={{ display: "inline-block", marginTop: "1rem" }}>
              Create Your First Event ➔
            </Link>
          </div>
        ) : (
          <div className="organizer-events-grid">
            {events.map((ev) => {
              const cap = ev.capacity || 100;
              const reg = ev.registered_count || 0;
              const pct = Math.min(100, Math.round((reg / cap) * 100));

              return (
                <div key={ev.id} className="organizer-event-card">
                  <div className="org-card-top">
                    <div>
                      <span className={`badge badge-${ev.status}`}>{ev.status?.toUpperCase()}</span>
                      <h3 style={{ marginTop: "0.4rem" }}>
                        <Link to={`/events/${ev.id}`}>{ev.name}</Link>
                      </h3>
                      <p style={{ fontSize: "0.85rem", color: "#64748b" }}>
                        📅 {ev.date} · ⏰ {ev.time} · 📍 {ev.venue_name || "Online / Venue TBA"}
                      </p>
                    </div>
                  </div>

                  <div className="org-card-stats">
                    <div className="org-stat-item">
                      <span>Registered</span>
                      <strong>{reg} / {cap}</strong>
                    </div>
                    <div className="org-stat-item">
                      <span>Checked In</span>
                      <strong style={{ color: "#059669" }}>{ev.attended_count || 0}</strong>
                    </div>
                    <div className="org-stat-item">
                      <span>Waitlist</span>
                      <strong style={{ color: "#d97706" }}>{ev.waitlisted_count || 0}</strong>
                    </div>
                  </div>

                  {/* Progress */}
                  <div className="progress-track" style={{ margin: "0.75rem 0", height: "8px" }}>
                    <div
                      className={`progress-fill ${reg >= cap ? "fill-full" : pct > 75 ? "fill-warn" : ""}`}
                      style={{ width: `${pct}%` }}
                    ></div>
                  </div>

                  <div className="org-card-actions">
                    <Link to="/attendance" className="btn btn-primary btn-sm">
                      Check-In Scanner
                    </Link>
                    <Link to="/registration" className="btn btn-outline btn-sm">
                      Attendees
                    </Link>
                    <button
                      className="btn btn-outline btn-sm"
                      onClick={() => api.downloadExport(`/reports/export/attendees?event_id=${ev.id}`, `attendees_event_${ev.id}.csv`)}
                    >
                      📥 CSV
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Quick Launch Console */}
      <div className="card">
        <h2>Operations & Resource Console</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem" }}>
          <Link to="/venues" className="console-nav-box">
            <span className="console-icon">🏛️</span>
            <h4>Venues</h4>
            <p>Assign and book venue spaces</p>
          </Link>
          <Link to="/resources" className="console-nav-box">
            <span className="console-icon">📦</span>
            <h4>Resources</h4>
            <p>Allocate AV gear, microphones and kits</p>
          </Link>
          <Link to="/vendors" className="console-nav-box">
            <span className="console-icon">🤝</span>
            <h4>Vendors</h4>
            <p>Contract caterers, decors and sound crews</p>
          </Link>
          <Link to="/report" className="console-nav-box">
            <span className="console-icon">📑</span>
            <h4>Reports</h4>
            <p>Comprehensive event statements & CSV exports</p>
          </Link>
        </div>
      </div>
    </div>
  );
}
