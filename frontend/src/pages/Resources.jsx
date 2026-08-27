import { useEffect, useState } from "react";
import { api } from "../api/api";
import { useAuth } from "../context/AuthContext";

const EMPTY_RES = { name: "", quantity: "" };
const EMPTY_ALLOC = { event_id: "", resource_id: "", quantity_used: "" };

export default function Resources() {
  const [resources, setResources] = useState([]);
  const [events, setEvents] = useState([]);
  const [allocations, setAllocations] = useState([]);
  const [resForm, setResForm] = useState(EMPTY_RES);
  const [allocForm, setAllocForm] = useState(EMPTY_ALLOC);
  const [msg, setMsg] = useState(null);
  const { isOrganizer, isAdmin } = useAuth();

  const load = () =>
    Promise.all([api.getResources(), api.getEvents(), api.getAllocations()]).then(
      ([r, e, a]) => {
        setResources(r);
        setEvents(e);
        setAllocations(a);
      }
    );

  useEffect(() => {
    load();
  }, []);

  const flash = (text, type = "success") => {
    setMsg({ text, type });
    setTimeout(() => setMsg(null), 3500);
  };

  const handleAddResource = async (e) => {
    e.preventDefault();
    try {
      await api.addResource({ ...resForm, quantity: parseInt(resForm.quantity) });
      flash("Resource added to inventory!");
      setResForm(EMPTY_RES);
      load();
    } catch (err) {
      flash(err.message, "error");
    }
  };

  const handleAllocate = async (e) => {
    e.preventDefault();
    try {
      await api.allocateResource({
        event_id: parseInt(allocForm.event_id),
        resource_id: parseInt(allocForm.resource_id),
        quantity_used: parseInt(allocForm.quantity_used),
      });
      flash("Resource allocated to event!");
      setAllocForm(EMPTY_ALLOC);
      load();
    } catch (err) {
      flash(err.message, "error");
    }
  };

  const handleDeallocate = async (id) => {
    if (!confirm("Release this resource back to inventory?")) return;
    try {
      await api.deallocateResource(id);
      flash("Resource released back to inventory.");
      load();
    } catch (err) {
      flash(err.message, "error");
    }
  };

  const handleDeleteResource = async (id, name) => {
    if (!confirm(`Delete resource '${name}'?`)) return;
    try {
      await api.deleteResource(id);
      flash("Resource deleted!");
      load();
    } catch (err) {
      flash(err.message, "error");
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Resource & Equipment Inventory</h1>
        <p>Manage audio-visual gear, projection units, badge kits, and allocate them to events</p>
      </div>

      {msg && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}

      {/* Forms (Organizers / Admins) */}
      {isOrganizer && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.5rem" }}>
          {/* Add Resource */}
          <div className="card">
            <h2>Add New Resource</h2>
            <form onSubmit={handleAddResource}>
              <div className="form-grid">
                <div className="form-group" style={{ gridColumn: "span 2" }}>
                  <label>Resource / Equipment Name</label>
                  <input
                    required
                    value={resForm.name}
                    onChange={(e) => setResForm({ ...resForm, name: e.target.value })}
                    placeholder="e.g. 4K Ultra Laser Projector"
                  />
                </div>
                <div className="form-group" style={{ gridColumn: "span 2" }}>
                  <label>Available Quantity Units</label>
                  <input
                    type="number"
                    required
                    min="1"
                    value={resForm.quantity}
                    onChange={(e) => setResForm({ ...resForm, quantity: e.target.value })}
                    placeholder="10"
                  />
                </div>
              </div>
              <div className="btn-row">
                <button type="submit" className="btn btn-primary">
                  Add to Inventory
                </button>
              </div>
            </form>
          </div>

          {/* Allocate Resource */}
          <div className="card">
            <h2>Allocate Resource to Event</h2>
            <form onSubmit={handleAllocate}>
              <div className="form-grid">
                <div className="form-group">
                  <label>Target Event</label>
                  <select
                    required
                    value={allocForm.event_id}
                    onChange={(e) => setAllocForm({ ...allocForm, event_id: e.target.value })}
                  >
                    <option value="">-- choose event --</option>
                    {events.map((ev) => (
                      <option key={ev.id} value={ev.id}>
                        {ev.name} ({ev.date})
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label>Equipment Item</label>
                  <select
                    required
                    value={allocForm.resource_id}
                    onChange={(e) => setAllocForm({ ...allocForm, resource_id: e.target.value })}
                  >
                    <option value="">-- choose resource --</option>
                    {resources
                      .filter((r) => r.quantity > 0)
                      .map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.name} ({r.quantity} available)
                        </option>
                      ))}
                  </select>
                </div>
                <div className="form-group" style={{ gridColumn: "span 2" }}>
                  <label>Quantity to Reserve</label>
                  <input
                    type="number"
                    required
                    min="1"
                    value={allocForm.quantity_used}
                    onChange={(e) => setAllocForm({ ...allocForm, quantity_used: e.target.value })}
                    placeholder="1"
                  />
                </div>
              </div>
              <div className="btn-row">
                <button type="submit" className="btn btn-success">
                  Confirm Allocation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Resources Table */}
      <div className="card" style={{ marginTop: isOrganizer ? "1.5rem" : 0 }}>
        <h2>Available Resource Inventory ({resources.length})</h2>
        {resources.length === 0 ? (
          <p className="empty-state">No equipment in inventory.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Item Name</th>
                  <th>Units In Stock</th>
                  <th>Status</th>
                  {isAdmin && <th>Actions</th>}
                </tr>
              </thead>
              <tbody>
                {resources.map((r) => (
                  <tr key={r.id}>
                    <td>{r.id}</td>
                    <td>
                      <strong>{r.name}</strong>
                    </td>
                    <td>
                      <strong>{r.quantity}</strong> units
                    </td>
                    <td>
                      <span className={`badge ${r.quantity > 0 ? "badge-available" : "badge-unavailable"}`}>
                        {r.quantity > 0 ? "In Stock" : "Exhausted"}
                      </span>
                    </td>
                    {isAdmin && (
                      <td>
                        <button
                          className="btn btn-danger btn-sm"
                          onClick={() => handleDeleteResource(r.id, r.name)}
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

      {/* Active Allocations Table */}
      <div className="card">
        <h2>Active Equipment Allocations ({allocations.length})</h2>
        {allocations.length === 0 ? (
          <p className="empty-state">No resources currently allocated.</p>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Event Name</th>
                  <th>Reserved Resource</th>
                  <th>Units Reserved</th>
                  {isOrganizer && <th>Action</th>}
                </tr>
              </thead>
              <tbody>
                {allocations.map((a) => (
                  <tr key={a.id}>
                    <td>{a.id}</td>
                    <td>
                      <strong>{a.event_name}</strong>
                    </td>
                    <td>{a.resource_name}</td>
                    <td>
                      <strong>{a.quantity_used}</strong> units
                    </td>
                    {isOrganizer && (
                      <td>
                        <button
                          className="btn btn-warning btn-sm"
                          onClick={() => handleDeallocate(a.id)}
                        >
                          Release Resource
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
