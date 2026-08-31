import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { api } from "../api/api";
import QRScannerModal from "../components/QRScannerModal";

export default function Attendance() {
  const [events, setEvents] = useState([]);
  const [eventId, setEventId] = useState("");
  const [attendance, setAttendance] = useState(null);
  const [checkinLogs, setCheckinLogs] = useState([]);
  const [qrMap, setQrMap] = useState({});
  const [search, setSearch] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [showScanner, setShowScanner] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    api.getEvents().then((evList) => {
      setEvents(evList);
      if (evList.length > 0) {
        setEventId(String(evList[0].id));
        loadAttendance(evList[0].id);
      }
    });
  }, []);

  const flash = (text, type = "success") => {
    setMsg({ text, type });
    setTimeout(() => setMsg(null), 3500);
  };

  const loadAttendance = async (eid) => {
    if (!eid) return;
    try {
      const [data, logs] = await Promise.all([
        api.getAttendance(eid),
        api.getCheckinLogs(eid).catch(() => []),
      ]);
      setAttendance(data);
      setCheckinLogs(logs);

      const map = {};
      for (const a of data.attendees) {
        if (a.ticket_id) {
          map[a.id] = await QRCode.toDataURL(
            a.qr_token || `ESP:${a.ticket_id}:${eid}:${a.id}:AUTO`,
            { width: 80, margin: 1 }
          );
        }
      }
      setQrMap(map);
    } catch (err) {
      flash(err.message || "Failed to load attendance", "error");
    }
  };

  const handleEventChange = (e) => {
    const val = e.target.value;
    setEventId(val);
    setAttendance(null);
    setCheckinLogs([]);
    setQrMap({});
    if (val) loadAttendance(val);
  };

  const handleCheckin = async (id) => {
    try {
      await api.checkin(id);
      flash("Attendee verified and checked in!");
      loadAttendance(eventId);
    } catch (err) {
      flash(err.message, "error");
    }
  };

  const handleAbsent = async (id) => {
    try {
      await api.markAbsent(id);
      flash("Attendee marked as absent.");
      loadAttendance(eventId);
    } catch (err) {
      flash(err.message, "error");
    }
  };

  const filteredAttendees = (attendance?.attendees || []).filter((a) => {
    const matchSearch =
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.email.toLowerCase().includes(search.toLowerCase()) ||
      (a.ticket_id && a.ticket_id.toLowerCase().includes(search.toLowerCase()));
    const matchStatus = filterStatus === "all" || a.status === filterStatus;
    return matchSearch && matchStatus;
  });

  return (
    <div>
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
          <div>
            <h1>Event Check-In & Attendance Verification</h1>
            <p>Scan participant QR codes, verify tickets, and manage real-time event check-ins</p>
          </div>
          <div className="btn-row" style={{ margin: 0 }}>
            <button
              className="btn btn-primary"
              style={{ fontSize: "1rem", padding: "0.6rem 1.2rem" }}
              onClick={() => setShowScanner(true)}
            >
              📷 Launch QR Scanner Terminal
            </button>
            {eventId && (
              <button
                className="btn btn-outline"
                onClick={() =>
                  api.downloadExport(
                    `/reports/export/attendees?event_id=${eventId}`,
                    `attendance_event_${eventId}.csv`
                  )
                }
              >
                📥 Export CSV
              </button>
            )}
          </div>
        </div>
      </div>

      {msg && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}

      {/* Event Selector Card */}
      <div className="card">
        <h2>Select Event to Manage</h2>
        <div className="form-group" style={{ maxWidth: "450px" }}>
          <select value={eventId} onChange={handleEventChange}>
            <option value="">-- Choose an Event --</option>
            {events.map((ev) => (
              <option key={ev.id} value={ev.id}>
                {ev.name} ({ev.date}) — {ev.venue_name || "Online"}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Attendance Stats Cards */}
      {attendance && (
        <>
          <div className="stat-row">
            <div className="stat-card">
              <div className="stat-value">{attendance.total}</div>
              <div className="stat-label">Total Registered</div>
            </div>
            <div className="stat-card" style={{ background: "#059669" }}>
              <div className="stat-value">{attendance.attended}</div>
              <div className="stat-label">Verified Checked-In</div>
            </div>
            <div className="stat-card" style={{ background: "#d97706" }}>
              <div className="stat-value">{attendance.registered}</div>
              <div className="stat-label">Pending Check-In</div>
            </div>
            <div className="stat-card" style={{ background: "#dc2626" }}>
              <div className="stat-value">{attendance.absent}</div>
              <div className="stat-label">Marked Absent</div>
            </div>
            {attendance.waitlisted > 0 && (
              <div className="stat-card" style={{ background: "#7c3aed" }}>
                <div className="stat-value">{attendance.waitlisted}</div>
                <div className="stat-label">Waitlist Queue</div>
              </div>
            )}
          </div>

          {/* Attendee Roster Table */}
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.75rem" }}>
              <h2>Attendee Roster ({filteredAttendees.length})</h2>

              <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                <input
                  type="text"
                  placeholder="Search by name, email or ticket ID..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  style={{ minWidth: "240px" }}
                />
                <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}>
                  <option value="all">All Statuses</option>
                  <option value="registered">Pending Registered</option>
                  <option value="attended">Attended</option>
                  <option value="absent">Absent</option>
                  <option value="waitlisted">Waitlisted</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>
            </div>

            {filteredAttendees.length === 0 ? (
              <p className="empty-state">No attendees match your search or filter.</p>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>QR Pass</th>
                      <th>Ticket ID</th>
                      <th>Participant</th>
                      <th>Contact</th>
                      <th>Status</th>
                      <th>Check-In Time</th>
                      <th>Quick Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredAttendees.map((a) => (
                      <tr key={a.id}>
                        <td>
                          {qrMap[a.id] ? (
                            <img
                              src={qrMap[a.id]}
                              alt="QR"
                              style={{ width: 44, height: 44, borderRadius: "4px", border: "1px solid #cbd5e1" }}
                            />
                          ) : (
                            <span style={{ color: "#aaa" }}>—</span>
                          )}
                        </td>
                        <td>
                          <span style={{ fontFamily: "monospace", fontWeight: 700, color: "#1e293b" }}>
                            {a.ticket_id || "WAITLIST"}
                          </span>
                        </td>
                        <td>
                          <strong>{a.name}</strong>
                          <span style={{ display: "block", fontSize: "0.78rem", color: "#64748b" }}>
                            {a.college || "General"}
                          </span>
                        </td>
                        <td>
                          {a.email}
                          <span style={{ display: "block", fontSize: "0.78rem", color: "#64748b" }}>
                            {a.phone}
                          </span>
                        </td>
                        <td>
                          <span className={`badge badge-${a.status}`}>{a.status}</span>
                        </td>
                        <td>
                          {a.checkin_time ? (
                            <span style={{ color: "#059669", fontWeight: 600, fontSize: "0.82rem" }}>
                              ✔ {a.checkin_time}
                            </span>
                          ) : (
                            <span style={{ color: "#94a3b8", fontSize: "0.82rem" }}>Not checked in</span>
                          )}
                        </td>
                        <td>
                          <div className="btn-row" style={{ margin: 0 }}>
                            {a.status !== "attended" && a.status !== "cancelled" && a.status !== "waitlisted" && (
                              <button
                                className="btn btn-success btn-sm"
                                onClick={() => handleCheckin(a.id)}
                              >
                                ✔ Verify Check In
                              </button>
                            )}
                            {a.status === "attended" && (
                              <span style={{ color: "#059669", fontWeight: 700, fontSize: "0.85rem" }}>
                                Checked In
                              </span>
                            )}
                            {a.status !== "absent" && a.status !== "attended" && a.status !== "cancelled" && (
                              <button
                                className="btn btn-danger btn-sm"
                                onClick={() => handleAbsent(a.id)}
                              >
                                Mark Absent
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

          {/* Verified Check-In Audit Trail */}
          <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.75rem" }}>
              <div>
                <h2>🛡️ Attendance Audit Trail & Verified Check-Ins ({checkinLogs.length})</h2>
                <p style={{ fontSize: "0.85rem", color: "#64748b", margin: 0 }}>
                  Real-time scan logs recording verified ticket signatures, timestamps, and staff auditors
                </p>
              </div>
              <button
                className="btn btn-outline btn-sm"
                onClick={() => loadAttendance(eventId)}
              >
                🔄 Refresh Logs
              </button>
            </div>

            {checkinLogs.length === 0 ? (
              <p className="empty-state">No check-ins recorded for this event yet.</p>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Check-In Timestamp</th>
                      <th>Ticket ID</th>
                      <th>Attendee</th>
                      <th>Email / Contact</th>
                      <th>Verified By (Staff)</th>
                      <th>Scan Method</th>
                    </tr>
                  </thead>
                  <tbody>
                    {checkinLogs.map((log) => (
                      <tr key={log.id}>
                        <td style={{ whiteSpace: "nowrap", fontSize: "0.85rem", color: "#059669", fontWeight: 600 }}>
                          ✔ {log.checkin_time}
                        </td>
                        <td>
                          <span style={{ fontFamily: "monospace", fontWeight: 700, color: "#1e293b" }}>
                            {log.ticket_id}
                          </span>
                        </td>
                        <td>
                          <strong>{log.attendee_name}</strong>
                        </td>
                        <td>
                          {log.attendee_email}
                        </td>
                        <td>
                          <span className="badge badge-active" style={{ fontSize: "0.78rem" }}>
                            {log.staff_name || "Authorized Staff"} ({log.staff_role || "organizer"})
                          </span>
                        </td>
                        <td>
                          <span className="badge badge-outline" style={{ fontSize: "0.75rem", textTransform: "uppercase" }}>
                            {log.method === "qr" ? "📷 QR Payload" : "⌨️ Manual Key"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {/* QR Scanner Modal Terminal */}
      {showScanner && (
        <QRScannerModal
          eventId={eventId}
          onCheckinSuccess={(res) => {
            flash(`Check-in verified for ${res.attendee?.name}!`);
            loadAttendance(eventId);
          }}
          onClose={() => setShowScanner(false)}
        />
      )}
    </div>
  );
}

