import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/api";
import TicketPass from "../components/TicketPass";

export default function MyRegistrations() {
  const [registrations, setRegistrations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("all");
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [msg, setMsg] = useState(null);

  const flash = (text, type = "success") => {
    setMsg({ text, type });
    setTimeout(() => setMsg(null), 4000);
  };

  const loadRegistrations = async () => {
    setLoading(true);
    try {
      const data = await api.getMyRegistrations();
      setRegistrations(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRegistrations();
  }, []);

  const handleCancel = async (id, eventName) => {
    if (!confirm(`Are you sure you want to cancel your registration for '${eventName}'?`)) return;

    try {
      const res = await api.cancelRegistration(id);
      flash(res.message || "Registration cancelled successfully.");
      loadRegistrations();
    } catch (err) {
      flash(err.message || "Failed to cancel registration.", "error");
    }
  };

  const filtered = registrations.filter((r) => {
    if (activeTab === "all") return true;
    if (activeTab === "active") return r.status === "registered";
    if (activeTab === "waitlist") return r.status === "waitlisted";
    if (activeTab === "attended") return r.status === "attended";
    if (activeTab === "cancelled") return r.status === "cancelled";
    return true;
  });

  return (
    <div>
      <div className="page-header">
        <h1>My Registrations & Event Passes</h1>
        <p>View your confirmed digital passes, check waitlist status, and manage attendance</p>
      </div>

      {msg && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}

      {/* Tabs */}
      <div className="filter-tabs-row">
        <button
          className={`filter-tab ${activeTab === "all" ? "active" : ""}`}
          onClick={() => setActiveTab("all")}
        >
          All Passes ({registrations.length})
        </button>
        <button
          className={`filter-tab ${activeTab === "active" ? "active" : ""}`}
          onClick={() => setActiveTab("active")}
        >
          Confirmed ({registrations.filter((r) => r.status === "registered").length})
        </button>
        <button
          className={`filter-tab ${activeTab === "waitlist" ? "active" : ""}`}
          onClick={() => setActiveTab("waitlist")}
        >
          Waitlisted ({registrations.filter((r) => r.status === "waitlisted").length})
        </button>
        <button
          className={`filter-tab ${activeTab === "attended" ? "active" : ""}`}
          onClick={() => setActiveTab("attended")}
        >
          Attended ({registrations.filter((r) => r.status === "attended").length})
        </button>
      </div>

      {loading ? (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Loading your event passes...</p>
        </div>
      ) : filtered.length === 0 ? (
        <div className="card empty-registrations-card">
          <div style={{ fontSize: "3rem", marginBottom: "0.5rem" }}>🎟️</div>
          <h3>No event passes found in this section</h3>
          <p>Explore upcoming events and register to receive instant verified tickets.</p>
          <Link to="/explore" className="btn btn-primary" style={{ display: "inline-block", marginTop: "1rem" }}>
            Explore Available Events ➔
          </Link>
        </div>
      ) : (
        <div className="registrations-grid">
          {filtered.map((r) => (
            <div key={r.id} className="card my-reg-card">
              <div className="my-reg-header">
                <span className={`badge badge-${r.status}`}>{r.status?.toUpperCase()}</span>
                {r.ticket_id && <span className="ticket-code-badge">{r.ticket_id}</span>}
              </div>

              <h3 className="my-reg-title">
                <Link to={`/events/${r.event_id}`}>{r.event_name}</Link>
              </h3>

              <div className="my-reg-details">
                <p>
                  <strong>📅 Date:</strong> {r.event_date} · {r.event_time}
                </p>
                <p>
                  <strong>📍 Location:</strong> {r.venue_name || (r.is_online ? "🌐 Online Live Stream" : "TBA")}
                </p>
                <p>
                  <strong>👤 Registered as:</strong> {r.name} ({r.email})
                </p>
                {r.checkin_time && (
                  <p style={{ color: "#10b981" }}>
                    <strong>✔ Checked In:</strong> {r.checkin_time}
                  </p>
                )}
              </div>

              <div className="my-reg-actions">
                {r.status === "registered" || r.status === "attended" ? (
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => setSelectedTicket(r)}
                  >
                    🎫 View Digital Pass & QR
                  </button>
                ) : r.status === "waitlisted" ? (
                  <span className="waitlist-pill">⏳ In Waitlist Queue</span>
                ) : null}

                {r.status !== "cancelled" && r.status !== "attended" && (
                  <button
                    className="btn btn-danger btn-sm"
                    onClick={() => handleCancel(r.id, r.event_name)}
                  >
                    Cancel Registration
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Ticket Pass Modal */}
      {selectedTicket && (
        <TicketPass
          ticket={selectedTicket}
          onClose={() => setSelectedTicket(null)}
        />
      )}
    </div>
  );
}
