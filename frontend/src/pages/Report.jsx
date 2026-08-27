import { useEffect, useState } from "react";
import { api } from "../api/api";

export default function Report() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api.getReport().then((r) => {
      setReport(r);
      setLoading(false);
    });
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) {
    return (
      <div className="loading-state">
        <div className="spinner"></div>
        <p>Aggregating platform reports...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h1>Comprehensive Master Event Report</h1>
            <p>Complete executive summary of all events, attendance figures, venue bookings, resources, and vendors</p>
          </div>
          <div className="btn-row" style={{ margin: 0 }}>
            <button
              className="btn btn-outline"
              onClick={() => api.downloadExport("/reports/export/events", "events_master_report.csv")}
            >
              📥 Export Events CSV
            </button>
            <button
              className="btn btn-primary"
              onClick={() => api.downloadExport("/reports/export/attendees", "all_attendees_export.csv")}
            >
              📥 Export All Attendees CSV
            </button>
          </div>
        </div>
      </div>

      {/* Summary stats */}
      <div className="stat-row">
        <div className="stat-card">
          <div className="stat-value">{report.total_events}</div>
          <div className="stat-label">Total Events Managed</div>
        </div>
        <div className="stat-card" style={{ background: "#4338ca" }}>
          <div className="stat-value">₹{Number(report.total_budget).toLocaleString()}</div>
          <div className="stat-label">Total Budget Committed</div>
        </div>
        <div className="stat-card" style={{ background: "#059669" }}>
          <div className="stat-value">{report.total_attendees}</div>
          <div className="stat-label">Total Registrations</div>
        </div>
        <div className="stat-card" style={{ background: "#7c3aed" }}>
          <div className="stat-value">{report.total_vendors}</div>
          <div className="stat-label">Contracted Vendors</div>
        </div>
      </div>

      {/* Per-event detail */}
      {report.events.map((ev) => (
        <div key={ev.id} className="card report-event-card">
          <div className="report-card-header">
            <div>
              <strong style={{ fontSize: "1.1rem", color: "#0f172a" }}>{ev.name}</strong>
              <div style={{ fontSize: "0.85rem", color: "#64748b", marginTop: "0.2rem" }}>
                <span>🏷️ {ev.category || ev.event_type}</span> · <span>📅 {ev.date} at {ev.time}</span>
              </div>
            </div>
            <span className={`badge badge-${ev.status}`}>{ev.status?.toUpperCase()}</span>
          </div>

          <div className="report-metrics-grid">
            <div className="report-metric-box">
              <label>Venue / Location</label>
              <p>{ev.venue_name || (ev.is_online ? "🌐 Virtual Live Room" : "Not Assigned")}</p>
            </div>
            <div className="report-metric-box">
              <label>Budget</label>
              <p>₹{Number(ev.budget).toLocaleString()}</p>
            </div>
            <div className="report-metric-box">
              <label>Capacity & Attendance</label>
              <p>
                {ev.attendees?.total
                  ? `${ev.attendees.attended || 0} checked in / ${ev.attendees.total} registered (Cap: ${ev.capacity || 100})`
                  : "No registrations yet"}
              </p>
            </div>
            <div className="report-metric-box">
              <label>Resources Allocated</label>
              <p>
                {ev.resources.length > 0
                  ? ev.resources.map((r) => `${r.name} (${r.quantity_used})`).join(", ")
                  : "None"}
              </p>
            </div>
            <div className="report-metric-box">
              <label>Contracted Vendors</label>
              <p>
                {ev.vendors.length > 0
                  ? ev.vendors.map((v) => `${v.name} [${v.service_type}]`).join(", ")
                  : "None"}
              </p>
            </div>
          </div>
        </div>
      ))}

      {report.events.length === 0 && <p className="empty-state">No events found in the database.</p>}

      <div style={{ textAlign: "right", marginTop: "1rem" }}>
        <button className="btn btn-primary" onClick={load}>
          🔄 Refresh Live Report
        </button>
      </div>
    </div>
  );
}
