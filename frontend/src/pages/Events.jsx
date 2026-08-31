import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/api";
import { useAuth } from "../context/AuthContext";

const EMPTY = {
  name: "",
  event_type: "Conference",
  category: "Technology",
  date: "",
  time: "",
  end_time: "",
  budget: "",
  capacity: 100,
  registration_deadline: "",
  description: "",
  is_online: false,
  meeting_link: "",
  visibility: "public",
  status: "draft",
};

const EVENT_TYPES = ["Conference", "Seminar", "Workshop", "Hackathon", "Cultural Fest", "Sports Meet", "Webinar", "Other"];
const CATEGORIES = ["Technology", "Management", "Cultural", "Sports", "Workshop", "Conference", "Hackathon", "Seminar", "Leadership"];
const _STATUSES = ["draft", "published", "ongoing", "completed", "cancelled"];

export default function Events() {
  const [events, setEvents] = useState([]);
  const [venues, setVenues] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [editingId, setEditingId] = useState(null);
  const [editingLocked, setEditingLocked] = useState(false);
  const [assignId, setAssignId] = useState(null);
  const [venueId, setVenueId] = useState("");
  const [msg, setMsg] = useState(null);
  const [search, setSearch] = useState("");
  const [filterCat, setFilterCat] = useState("All");
  const { isOrganizer } = useAuth();

  const load = () =>
    Promise.all([api.getEvents(), api.getVenues()]).then(([ev, vn]) => {
      setEvents(ev);
      setVenues(vn);
    });

  useEffect(() => {
    load();
  }, []);

  const flash = (text, type = "success") => {
    setMsg({ text, type });
    setTimeout(() => setMsg(null), 3500);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const payload = {
      ...form,
      budget: parseFloat(form.budget || 0),
      capacity: parseInt(form.capacity || 100),
    };

    try {
      if (editingId) {
        await api.updateEvent(editingId, payload);
        flash("Event updated successfully!");
      } else {
        await api.createEvent(payload);
        flash(`Event created successfully in '${payload.status.toUpperCase()}' status!`);
      }
      setForm(EMPTY);
      setEditingId(null);
      setEditingLocked(false);
      load();
    } catch (err) {
      flash(err.message, "error");
    }
  };

  const handleEdit = (ev) => {
    const isLocked = ev.status === "completed" || ev.status === "cancelled";
    setEditingLocked(isLocked);
    setForm({
      name: ev.name,
      event_type: ev.event_type,
      category: ev.category || "Technology",
      date: ev.date,
      time: ev.time,
      end_time: ev.end_time || "",
      budget: ev.budget,
      capacity: ev.capacity || 100,
      registration_deadline: ev.registration_deadline || "",
      description: ev.description || "",
      is_online: Boolean(ev.is_online),
      meeting_link: ev.meeting_link || "",
      visibility: ev.visibility || "public",
      status: ev.status,
    });
    setEditingId(ev.id);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleQuickTransition = async (ev, newStatus) => {
    if (newStatus === "cancelled" && !confirm(`Cancel event '${ev.name}'? This will automatically cancel all attendee registrations and tickets.`)) {
      return;
    }
    try {
      await api.updateEvent(ev.id, {
        ...ev,
        status: newStatus,
      });
      flash(`Event status transitioned to ${newStatus.toUpperCase()}`);
      load();
    } catch (err) {
      flash(err.message, "error");
    }
  };


  const handleDelete = async (id, name) => {
    if (!confirm(`Delete event '${name}'? This action cannot be undone.`)) return;
    try {
      await api.deleteEvent(id);
      flash("Event deleted successfully!");
      load();
    } catch (err) {
      flash(err.message, "error");
    }
  };

  const handleAssign = async (e) => {
    e.preventDefault();
    try {
      await api.assignVenue(assignId, parseInt(venueId));
      flash("Venue assigned successfully!");
      setAssignId(null);
      setVenueId("");
      load();
    } catch (err) {
      flash(err.message, "error");
    }
  };

  const cancelEdit = () => {
    setForm(EMPTY);
    setEditingId(null);
  };

  const filtered = events.filter((ev) => {
    const matchSearch =
      ev.name.toLowerCase().includes(search.toLowerCase()) ||
      (ev.category && ev.category.toLowerCase().includes(search.toLowerCase())) ||
      (ev.venue_name && ev.venue_name.toLowerCase().includes(search.toLowerCase()));
    const matchCat = filterCat === "All" || ev.category === filterCat;
    return matchSearch && matchCat;
  });

  return (
    <div>
      <div className="page-header">
        <h1>Event Management</h1>
        <p>Create, update, manage capacities and assign venue allocations</p>
      </div>

      {msg && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}

      {/* Form (Organizers / Admins) */}
      {isOrganizer && (
        <div className="card">
          <h2>{editingId ? `Edit Event #${editingId}` : "Create New Event"}</h2>
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="form-group" style={{ gridColumn: "span 2" }}>
                <label>Event Title</label>
                <input
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. National Hackathon & AI Conclave 2026"
                />
              </div>

              <div className="form-group">
                <label>Event Type</label>
                <select
                  value={form.event_type}
                  onChange={(e) => setForm({ ...form, event_type: e.target.value })}
                >
                  {EVENT_TYPES.map((t) => (
                    <option key={t}>{t}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Category</label>
                <select
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                >
                  {CATEGORIES.map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Date</label>
                <input
                  type="date"
                  required
                  value={form.date}
                  onChange={(e) => setForm({ ...form, date: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>Start Time</label>
                <input
                  type="time"
                  required
                  value={form.time}
                  onChange={(e) => setForm({ ...form, time: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>End Time (Optional)</label>
                <input
                  type="time"
                  value={form.end_time}
                  onChange={(e) => setForm({ ...form, end_time: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>Seat Capacity</label>
                <input
                  type="number"
                  required
                  min="1"
                  value={form.capacity}
                  onChange={(e) => setForm({ ...form, capacity: e.target.value })}
                  placeholder="100"
                />
              </div>

              <div className="form-group">
                <label>Registration Deadline</label>
                <input
                  type="date"
                  value={form.registration_deadline}
                  onChange={(e) => setForm({ ...form, registration_deadline: e.target.value })}
                />
              </div>

              <div className="form-group">
                <label>Budget (₹)</label>
                <input
                  type="number"
                  min="0"
                  value={form.budget}
                  onChange={(e) => setForm({ ...form, budget: e.target.value })}
                  placeholder="50000"
                />
              </div>

              <div className="form-group">
                <label>Lifecycle Status</label>
                <select
                  value={form.status}
                  onChange={(e) => setForm({ ...form, status: e.target.value })}
                >
                  <option value="draft">Draft (Private, not open for registration)</option>
                  <option value="published">Published (Active & Registrable)</option>
                  <option value="ongoing">Ongoing (In Progress)</option>
                  <option value="completed">Completed (Concluded)</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>

              <div className="form-group" style={{ gridColumn: "span 2" }}>
                <label>Description & Objectives</label>
                <textarea
                  rows={3}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="Provide details about speakers, agenda, target audience, and prerequisites..."
                  style={{
                    padding: "0.5rem 0.75rem",
                    border: "1px solid #c0d4e8",
                    borderRadius: "6px",
                    fontFamily: "inherit",
                    fontSize: "0.9rem",
                  }}
                />
              </div>

              <div className="form-group" style={{ display: "flex", flexDirection: "row", alignItems: "center", gap: "0.5rem" }}>
                <input
                  type="checkbox"
                  id="is_online"
                  checked={form.is_online}
                  onChange={(e) => setForm({ ...form, is_online: e.target.checked })}
                  style={{ width: "18px", height: "18px" }}
                />
                <label htmlFor="is_online" style={{ margin: 0, cursor: "pointer" }}>
                  Virtual / Online Event
                </label>
              </div>

              {form.is_online && (
                <div className="form-group" style={{ gridColumn: "span 2" }}>
                  <label>Virtual Meeting Link (Zoom / Teams / Meet)</label>
                  <input
                    type="url"
                    value={form.meeting_link}
                    onChange={(e) => setForm({ ...form, meeting_link: e.target.value })}
                    placeholder="https://meet.google.com/..."
                  />
                </div>
              )}
            </div>

            {editingLocked && (
              <div className="alert alert-warning" style={{ marginTop: "1rem" }}>
                🔒 <strong>Event Locked:</strong> This event is in <strong>{form.status.toUpperCase()}</strong> status. Its details cannot be modified.
              </div>
            )}

            <div className="btn-row" style={{ marginTop: "1rem" }}>
              <button
                type="submit"
                disabled={editingLocked}
                className={`btn ${editingId ? "btn-warning" : "btn-primary"}`}
              >
                {editingId ? "Save Event Changes" : "Create Event"}
              </button>
              {editingId && (
                <button type="button" className="btn btn-secondary" onClick={cancelEdit}>
                  Cancel Edit
                </button>
              )}
            </div>
          </form>
        </div>
      )}

      {/* Assign Venue Modal */}
      {assignId && (
        <div className="card">
          <h2>Assign Venue — Event #{assignId}</h2>
          <form onSubmit={handleAssign}>
            <div className="form-grid">
              <div className="form-group">
                <label>Select Available Venue</label>
                <select
                  required
                  value={venueId}
                  onChange={(e) => setVenueId(e.target.value)}
                >
                  <option value="">-- choose venue --</option>
                  {venues
                    .filter((v) => v.availability)
                    .map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.name} (Cap: {v.capacity} · {v.location})
                      </option>
                    ))}
                </select>
              </div>
            </div>
            <div className="btn-row">
              <button type="submit" className="btn btn-success">
                Confirm Venue Assignment
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setAssignId(null)}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Events Table */}
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.75rem" }}>
          <h2>All Events Registry ({filtered.length})</h2>

          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <input
              type="text"
              placeholder="Filter by name, venue or category..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ minWidth: "220px" }}
            />
            <select value={filterCat} onChange={(e) => setFilterCat(e.target.value)}>
              <option value="All">All Categories</option>
              {CATEGORIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </div>
        </div>

        {filtered.length === 0 ? (
          <p className="empty-state">No events matching your filter.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Event Name</th>
                  <th>Category</th>
                  <th>Date & Time Window</th>
                  <th>Capacity & Reg</th>
                  <th>Lifecycle Status</th>
                  <th>Venue / Format</th>
                  <th>Actions & Lifecycle</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((ev) => {
                  const cap = ev.capacity || 100;
                  const reg = ev.registered_count || 0;
                  return (
                    <tr key={ev.id}>
                      <td>{ev.id}</td>
                      <td>
                        <strong>
                          <Link to={`/events/${ev.id}`}>{ev.name}</Link>
                        </strong>
                      </td>
                      <td>
                        <span className="badge badge-planned">{ev.category || ev.event_type}</span>
                      </td>
                      <td>
                        {ev.date} <br />
                        <span style={{ fontSize: "0.78rem", color: "#64748b" }}>
                          {ev.time} {ev.end_time ? `– ${ev.end_time}` : ""}
                        </span>
                      </td>
                      <td>
                        <strong>{reg} / {cap}</strong>
                        {ev.waitlisted_count > 0 && (
                          <span style={{ color: "#d97706", fontSize: "0.75rem", display: "block" }}>
                            +{ev.waitlisted_count} waitlisted
                          </span>
                        )}
                      </td>
                      <td>
                        <span className={`badge badge-${ev.status}`}>
                          {ev.status?.toUpperCase()}
                        </span>
                      </td>
                      <td>
                        {ev.is_online ? (
                          <span style={{ color: "#2563eb", fontWeight: 600 }}>🌐 Online</span>
                        ) : (
                          ev.venue_name || <span style={{ color: "#aaa" }}>Unassigned</span>
                        )}
                      </td>
                      <td>
                        <div className="btn-row" style={{ margin: 0, gap: "0.3rem" }}>
                          <Link to={`/events/${ev.id}`} className="btn btn-primary btn-sm">
                            View
                          </Link>
                          {isOrganizer && (
                            <>
                              {ev.status === "draft" && (
                                <button
                                  className="btn btn-success btn-sm"
                                  title="Publish event to attendees"
                                  onClick={() => handleQuickTransition(ev, "published")}
                                >
                                  🚀 Publish
                                </button>
                              )}
                              {ev.status === "published" && (
                                <button
                                  className="btn btn-warning btn-sm"
                                  title="Cancel event and notify attendees"
                                  onClick={() => handleQuickTransition(ev, "cancelled")}
                                >
                                  🚫 Cancel
                                </button>
                              )}
                              {ev.status === "ongoing" && (
                                <button
                                  className="btn btn-info btn-sm"
                                  title="Mark event as completed"
                                  onClick={() => handleQuickTransition(ev, "completed")}
                                >
                                  🏁 Complete
                                </button>
                              )}
                              {ev.status !== "completed" && ev.status !== "cancelled" && (
                                <>
                                  <button className="btn btn-outline btn-sm" onClick={() => handleEdit(ev)}>
                                    Edit
                                  </button>
                                  <button
                                    className="btn btn-outline btn-sm"
                                    onClick={() => {
                                      setAssignId(ev.id);
                                      setVenueId("");
                                    }}
                                  >
                                    Venue
                                  </button>
                                </>
                              )}
                              <button
                                className="btn btn-danger btn-sm"
                                onClick={() => handleDelete(ev.id, ev.name)}
                              >
                                Delete
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
