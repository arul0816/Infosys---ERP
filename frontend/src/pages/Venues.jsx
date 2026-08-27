import { useEffect, useState } from "react";
import { api } from "../api/api";
import { useAuth } from "../context/AuthContext";

const EMPTY = { name: "", capacity: "", location: "" };

export default function Venues() {
  const [venues, setVenues] = useState([]);
  const [form, setForm] = useState(EMPTY);
  const [msg, setMsg] = useState(null);
  const { isOrganizer, isAdmin } = useAuth();

  const load = () => api.getVenues().then(setVenues);
  useEffect(() => {
    load();
  }, []);

  const flash = (text, type = "success") => {
    setMsg({ text, type });
    setTimeout(() => setMsg(null), 3500);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await api.addVenue({ ...form, capacity: parseInt(form.capacity) });
      flash("Venue created and added to inventory!");
      setForm(EMPTY);
      load();
    } catch (err) {
      flash(err.message, "error");
    }
  };

  const handleDelete = async (id, name) => {
    if (!confirm(`Delete venue '${name}'?`)) return;
    try {
      await api.deleteVenue(id);
      flash("Venue deleted successfully!");
      load();
    } catch (err) {
      flash(err.message, "error");
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Venue Management & Spaces</h1>
        <p>Explore facilities, seating capacities, and assign venues to scheduled events</p>
      </div>

      {msg && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}

      {/* Add Venue (Organizers / Admins) */}
      {isOrganizer && (
        <div className="card">
          <h2>Add New Venue Space</h2>
          <form onSubmit={handleSubmit}>
            <div className="form-grid">
              <div className="form-group" style={{ gridColumn: "span 2" }}>
                <label>Venue / Hall Name</label>
                <input
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. Infosys Convention Center - Hall A"
                />
              </div>
              <div className="form-group">
                <label>Seating Capacity</label>
                <input
                  type="number"
                  required
                  min="1"
                  value={form.capacity}
                  onChange={(e) => setForm({ ...form, capacity: e.target.value })}
                  placeholder="500"
                />
              </div>
              <div className="form-group">
                <label>Location / Floor Details</label>
                <input
                  required
                  value={form.location}
                  onChange={(e) => setForm({ ...form, location: e.target.value })}
                  placeholder="e.g. Block C, 3rd Floor"
                />
              </div>
            </div>
            <div className="btn-row">
              <button type="submit" className="btn btn-primary">
                Add Venue to Directory
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Venue List */}
      <div className="card">
        <h2>All Available Venues ({venues.length})</h2>
        {venues.length === 0 ? (
          <p className="empty-state">No venues registered yet.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Venue Name</th>
                  <th>Max Capacity</th>
                  <th>Location</th>
                  <th>Availability</th>
                  {isAdmin && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {venues.map((v) => (
                  <tr key={v.id}>
                    <td>{v.id}</td>
                    <td>
                      <strong>{v.name}</strong>
                    </td>
                    <td>
                      <strong>{v.capacity}</strong> attendees
                    </td>
                    <td>{v.location}</td>
                    <td>
                      <span className={`badge ${v.availability ? "badge-available" : "badge-unavailable"}`}>
                        {v.availability ? "Available" : "Booked / Unavailable"}
                      </span>
                    </td>
                    {isAdmin && (
                      <td>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => handleDelete(v.id, v.name)}
                        >
                          Delete
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
