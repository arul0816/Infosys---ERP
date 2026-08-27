import { useEffect, useState } from "react";
import { api } from "../api/api";
import TicketPass from "../components/TicketPass";

const EMPTY = { event_id: "", name: "", email: "", phone: "", college: "" };

export default function Registration() {
  const [events, setEvents] = useState([]);
  const [regs, setRegs] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [selectedTicket, setSelectedTicket] = useState(null);
  const [filterEv, setFilterEv] = useState("");
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [msg, setMsg] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const load = () =>
    Promise.all([api.getEvents(), api.getAllRegistrations()]).then(([ev, r]) => {
      setEvents(ev);
      setRegs(r);
    });

  useEffect(() => {
    load();
  }, []);

  const flash = (text, type = "success") => {
    setMsg({ text, type });
    setTimeout(() => setMsg(null), 4000);
  };

  const selectedEventObj = events.find((e) => String(e.id) === String(form.event_id));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const result = await api.register({ ...form, event_id: parseInt(form.event_id) });

      if (result.status === "registered" && result.ticket_id) {
        flash(`Registration successful! Issued Ticket ID: ${result.ticket_id}`);
        setSelectedTicket({
          ...result,
          event_name: selectedEventObj?.name || `Event #${result.event_id}`,
          event_date: selectedEventObj?.date,
          event_time: selectedEventObj?.time,
          venue_name: selectedEventObj?.venue_name,
          college: form.college,
        });
      } else {
        flash(`Event is full. Added to Waitlist (Position #${result.waitlist_position})`, "warning");
      }

      setForm(EMPTY);
      load();
    } catch (err) {
      flash(err.message, "error");
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = async (id, name, eventName) => {
    if (!confirm(`Cancel registration for ${name} in '${eventName}'?`)) return;
    try {
      const res = await api.cancelRegistration(id);
      flash(res.message || "Registration cancelled.");
      load();
    } catch (err) {
      flash(err.message, "error");
    }
  };

  const filtered = regs.filter((r) => {
    const matchEvent = !filterEv || String(r.event_id) === filterEv;
    const matchStatus = filterStatus === "all" || r.status === filterStatus;
    const matchSearch =
      r.name.toLowerCase().includes(search.toLowerCase()) ||
      r.email.toLowerCase().includes(search.toLowerCase()) ||
      (r.ticket_id && r.ticket_id.toLowerCase().includes(search.toLowerCase())) ||
      (r.event_name && r.event_name.toLowerCase().includes(search.toLowerCase()));
    return matchEvent && matchStatus && matchSearch;
  });

  return (
    <div>
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h1>Participant Registrations Hub</h1>
            <p>Direct registration console, waitlist tracking, and digital ticket pass generator</p>
          </div>
          <button
            className="btn btn-outline"
            onClick={() =>
              api.downloadExport(
                `/reports/export/attendees${filterEv ? `?event_id=${filterEv}` : ""}`,
                `registrations_export.csv`
              )
            }
          >
            📥 Export Registrations CSV
          </button>
        </div>
      </div>

      {msg && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}

      {/* Registration Form Card */}
      <div className="card">
        <h2>Direct Participant Registration</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            <div className="form-group" style={{ gridColumn: "span 2" }}>
              <label>Select Target Event</label>
              <select
                required
                value={form.event_id}
                onChange={(e) => setForm({ ...form, event_id: e.target.value })}
              >
                <option value="">-- Choose an Event --</option>
                {events.map((ev) => (
                  <option key={ev.id} value={ev.id}>
                    {ev.name} ({ev.date}) — {ev.remaining_seats} seats remaining (Cap: {ev.capacity})
                  </option>
                ))}
              </select>
            </div>

            {selectedEventObj && (
              <div className="form-group" style={{ gridColumn: "span 2" }}>
                <div className="selected-event-preview">
                  <span>
                    <strong>{selectedEventObj.name}</strong> · 📅 {selectedEventObj.date} at {selectedEventObj.time} · 📍 {selectedEventObj.venue_name || "Online"}
                  </span>
                  <span style={{ color: selectedEventObj.is_full ? "#ef4444" : "#10b981", fontWeight: 700 }}>
                    {selectedEventObj.is_full ? "⚠️ Event Capacity Reached (Will Waitlist)" : `✔ ${selectedEventObj.remaining_seats} seats available`}
                  </span>
                </div>
              </div>
            )}

            <div className="form-group">
              <label>Full Name</label>
              <input
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. Arjun Kumar"
              />
            </div>

            <div className="form-group">
              <label>Email Address</label>
              <input
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="arjun@email.com"
              />
            </div>

            <div className="form-group">
              <label>Phone Number</label>
              <input
                required
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
                placeholder="9876543210"
              />
            </div>

            <div className="form-group">
              <label>College / Organization</label>
              <input
                value={form.college}
                onChange={(e) => setForm({ ...form, college: e.target.value })}
                placeholder="e.g. Infosys Ltd / Anna Univ"
              />
            </div>
          </div>

          <div className="btn-row" style={{ marginTop: "1rem" }}>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? "Processing..." : "Register & Issue Digital Ticket Pass"}
            </button>
          </div>
        </form>
      </div>

      {/* Registrations List Card */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.75rem" }}>
          <h2>All Registrations ({filtered.length})</h2>

          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <input
              type="text"
              placeholder="Search attendee, ticket ID, event..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ minWidth: "220px" }}
            />
            <select value={filterEv} onChange={(e) => setFilterEv(e.target.value)}>
              <option value="">All Events</option>
              {events.map((ev) => (
                <option key={ev.id} value={ev.id}>
                  {ev.name}
                </option>
              ))}
            </select>
            <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
              <option value="all">All Statuses</option>
              <option value="registered">Registered</option>
              <option value="waitlisted">Waitlisted</option>
              <option value="attended">Attended</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        </div>

        {filtered.length === 0 ? (
          <p className="empty-state">No registrations match your search filters.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Ticket ID</th>
                  <th>Participant</th>
                  <th>Contact</th>
                  <th>Event</th>
                  <th>Status</th>
                  <th>Registration Date</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <span style={{ fontFamily: "monospace", fontWeight: 700, color: "#1e293b" }}>
                        {r.ticket_id || "WAITLIST"}
                      </span>
                    </td>
                    <td>
                      <strong>{r.name}</strong>
                      <span style={{ display: "block", fontSize: "0.78rem", color: "#64748b" }}>
                        {r.college || "—"}
                      </span>
                    </td>
                    <td>
                      {r.email}
                      <span style={{ display: "block", fontSize: "0.78rem", color: "#64748b" }}>
                        {r.phone}
                      </span>
                    </td>
                    <td>{r.event_name}</td>
                    <td>
                      <span className={`badge badge-${r.status}`}>{r.status}</span>
                    </td>
                    <td style={{ fontSize: "0.82rem", color: "#64748b" }}>
                      {r.registered_at?.slice(0, 16) || "—"}
                    </td>
                    <td>
                      <div className="btn-row" style={{ margin: 0 }}>
                        {r.ticket_id && (
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => setSelectedTicket(r)}
                          >
                            Pass
                          </button>
                        )}
                        {r.status !== "cancelled" && (
                          <button
                            className="btn btn-danger btn-sm"
                            onClick={() => handleCancel(r.id, r.name, r.event_name)}
                          >
                            Cancel
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

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
