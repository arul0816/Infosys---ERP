import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/api";
import { useAuth } from "../context/AuthContext";
import TicketPass from "../components/TicketPass";

export default function EventDetail() {
  const { id } = useParams();
  const { user } = useAuth();

  const [event, setEvent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Registration Modal State
  const [showRegModal, setShowRegModal] = useState(false);
  const [regForm, setRegForm] = useState({
    name: "",
    email: "",
    phone: "",
    college: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [regResult, setRegResult] = useState(null);
  const [regError, setRegError] = useState(null);
  const [issuedTicket, setIssuedTicket] = useState(null);

  const loadEvent = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getEvent(id);
      setEvent(data);
    } catch (err) {
      setError(err.message || "Failed to load event details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvent();
  }, [id]);

  useEffect(() => {
    if (user) {
      setRegForm({
        name: user.name || "",
        email: user.email || "",
        phone: user.phone || "",
        college: user.organization || "",
      });
    }
  }, [user]);

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setRegError(null);
    setRegResult(null);

    try {
      const res = await api.register({
        ...regForm,
        event_id: parseInt(id),
      });

      setRegResult(res);
      if (res.status === "registered" && res.ticket_id) {
        setIssuedTicket({
          ...res,
          event_name: event.name,
          event_date: event.date,
          event_time: event.time,
          venue_name: event.venue_name,
          is_online: event.is_online,
          college: regForm.college,
        });
      }
      loadEvent(); // Refresh capacity
    } catch (err) {
      setRegError(err.message || "Registration failed.");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-state" style={{ minHeight: "50vh" }}>
        <div className="spinner"></div>
        <p>Loading event information...</p>
      </div>
    );
  }

  if (error || !event) {
    return (
      <div className="card" style={{ textAlign: "center", padding: "3rem 1.5rem", maxWidth: "600px", margin: "2rem auto" }}>
        <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>⚠️</div>
        <h2>Event Not Found</h2>
        <p style={{ color: "#64748b", margin: "1rem 0" }}>{error || "The requested event could not be located."}</p>
        <Link to="/explore" className="btn btn-primary">
          Explore Other Events
        </Link>
      </div>
    );
  }

  const cap = event.capacity || 100;
  const filled = event.registered_count || 0;
  const pct = Math.min(100, Math.round((filled / cap) * 100));
  const isFull = event.is_full;
  const isRegistrable = event.status === "published" || event.status === "ongoing";
  const deadlinePassed = event.registration_deadline && new Date().toISOString().slice(0, 10) > event.registration_deadline.slice(0, 10);
  const canRegister = isRegistrable && !deadlinePassed;

  return (
    <div className="event-detail-page">
      {/* Back link */}
      <div style={{ marginBottom: "1rem" }}>
        <Link to="/explore" className="back-link">
          ← Back to All Events
        </Link>
      </div>

      {/* Main Grid */}
      <div className="event-detail-grid">
        {/* Left Column: Details */}
        <div className="event-main-col">
          <div className="card event-hero-card">
            <div className="event-tag-row">
              <span className="card-cat-badge">{event.category || event.event_type}</span>
              <span className={`badge badge-${event.status}`}>{event.status?.toUpperCase()}</span>
              {event.is_online ? (
                <span className="card-format-badge format-online">🌐 Live Virtual Event</span>
              ) : (
                <span className="card-format-badge format-venue">🏛️ In-Person Venue</span>
              )}
            </div>

            <h1 className="event-hero-title">{event.name}</h1>

            <div className="event-highlights-grid">
              <div className="highlight-item">
                <span className="highlight-icon">📅</span>
                <div>
                  <label>Date</label>
                  <strong>{event.date}</strong>
                </div>
              </div>
              <div className="highlight-item">
                <span className="highlight-icon">⏰</span>
                <div>
                  <label>Time</label>
                  <strong>{event.time} {event.end_time ? `– ${event.end_time}` : ""}</strong>
                </div>
              </div>
              <div className="highlight-item">
                <span className="highlight-icon">📍</span>
                <div>
                  <label>Location / Venue</label>
                  <strong>{event.venue_name || (event.is_online ? "Online Link in Pass" : "To Be Announced")}</strong>
                </div>
              </div>
              <div className="highlight-item">
                <span className="highlight-icon">🎟️</span>
                <div>
                  <label>Registration Fee</label>
                  <strong style={{ color: "#10b981" }}>Free Entry</strong>
                </div>
              </div>
            </div>
          </div>

          {/* Description Section */}
          <div className="card">
            <h2>About This Event</h2>
            <div className="event-prose">
              <p>
                {event.description ||
                  "This event provides an exceptional platform for learning, collaboration, and professional enrichment. Attendees will engage with subject matter experts, participate in insightful discussions, and gain actionable takeaways."}
              </p>
            </div>

            {event.is_online && event.meeting_link && (
              <div className="online-instructions-card">
                <h4>🌐 Virtual Room Information</h4>
                <p>Meeting link and room details will be unlocked inside your confirmed digital pass.</p>
              </div>
            )}
          </div>

          {/* Organizer Card */}
          <div className="card organizer-card">
            <h2>Hosted by Organizer</h2>
            <div className="organizer-profile-row">
              <div className="organizer-avatar">
                {event.organizer_name?.charAt(0) || "E"}
              </div>
              <div>
                <h4>{event.organizer_name || "EventSphere Committee"}</h4>
                <p>{event.organizer_org || "Verified Organizer"}</p>
                {event.organizer_email && <span className="organizer-contact">✉️ {event.organizer_email}</span>}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Registration Card & Capacity */}
        <div className="event-sidebar-col">
          <div className="card registration-sidebar-card">
            <h3>Registration Status</h3>

            {/* Capacity Progress Ring / Bar */}
            <div className="capacity-stat-box">
              <div className="cap-numbers">
                <div>
                  <span className="cap-big-num">{event.remaining_seats}</span>
                  <span className="cap-label">Seats Remaining</span>
                </div>
                <div style={{ textAlign: "right" }}>
                  <span className="cap-sub-num">{filled} / {cap}</span>
                  <span className="cap-label">Capacity Filled</span>
                </div>
              </div>

              <div className="progress-track" style={{ height: "10px", margin: "1rem 0" }}>
                <div
                  className={`progress-fill ${isFull ? "fill-full" : pct > 75 ? "fill-warn" : ""}`}
                  style={{ width: `${pct}%` }}
                ></div>
              </div>

              {isFull && isRegistrable && !deadlinePassed && (
                <div className="waitlist-indicator">
                  <span>⏳ Capacity Reached: Waitlist is active. If registered participants cancel, seats are auto-promoted in order!</span>
                </div>
              )}
            </div>

            {event.registration_deadline && (
              <div className="deadline-notice" style={{ marginBottom: "1rem" }}>
                <span>⏱️ Registration Deadline:</span>
                <strong>{event.registration_deadline}</strong>
                {deadlinePassed && (
                  <span style={{ display: "block", color: "#dc2626", fontSize: "0.8rem", marginTop: "0.2rem" }}>
                    ⚠️ Registration deadline has passed
                  </span>
                )}
              </div>
            )}

            {!isRegistrable && (
              <div className="alert alert-warning" style={{ margin: "0.5rem 0 1rem 0", fontSize: "0.88rem" }}>
                {event.status === "draft" && "📝 Event is currently in DRAFT status and is not yet open for registrations."}
                {event.status === "completed" && "🏁 Event has concluded. Registrations are closed."}
                {event.status === "cancelled" && "🚫 Event has been cancelled. Registrations are inactive."}
              </div>
            )}

            <button
              className={`btn btn-block ${isFull ? "btn-warning" : "btn-primary"}`}
              style={{ padding: "0.85rem 1rem", fontSize: "1rem", opacity: canRegister ? 1 : 0.6 }}
              disabled={!canRegister}
              onClick={() => setShowRegModal(true)}
            >
              {!isRegistrable
                ? `Event ${event.status?.toUpperCase()}`
                : deadlinePassed
                ? "Registration Closed"
                : isFull
                ? "Join the Waitlist Now"
                : "Register for Event"}
            </button>

            <p style={{ fontSize: "0.78rem", color: "#64748b", textAlign: "center", marginTop: "0.75rem" }}>
              Instant digital ticket with secure QR pass generated upon confirmation.
            </p>
          </div>
        </div>
      </div>

      {/* Registration Modal Dialog */}
      {showRegModal && (
        <div className="modal-overlay" onClick={() => setShowRegModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "520px" }}>
            <div className="modal-header">
              <div>
                <h3>{isFull ? "Join Event Waitlist" : "Event Registration"}</h3>
                <p style={{ margin: 0, fontSize: "0.85rem", color: "#64748b" }}>{event.name}</p>
              </div>
              <button className="close-btn" onClick={() => setShowRegModal(false)}>✕</button>
            </div>

            {regError && <div className="alert alert-error">{regError}</div>}

            {regResult ? (
              <div className="reg-success-pane">
                <div style={{ fontSize: "3rem", marginBottom: "0.5rem" }}>
                  {regResult.status === "registered" ? "🎉" : "⏳"}
                </div>
                <h3>{regResult.message}</h3>

                {regResult.status === "registered" ? (
                  <>
                    <p>Your ticket has been generated and confirmed.</p>
                    <div className="btn-row" style={{ justifyContent: "center", marginTop: "1rem" }}>
                      <button
                        className="btn btn-primary"
                        onClick={() => {
                          setShowRegModal(false);
                        }}
                      >
                        View Digital Pass
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <p>
                      You are in queue position <strong>#{regResult.waitlist_position}</strong>. We will notify you when a slot becomes available.
                    </p>
                    <div className="btn-row" style={{ justifyContent: "center", marginTop: "1rem" }}>
                      <button className="btn btn-secondary" onClick={() => setShowRegModal(false)}>
                        Close
                      </button>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <form onSubmit={handleRegisterSubmit}>
                <div className="form-group">
                  <label>Full Name</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Arun Kumar"
                    value={regForm.name}
                    onChange={(e) => setRegForm({ ...regForm, name: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label>Email Address</label>
                  <input
                    type="email"
                    required
                    placeholder="arun@example.com"
                    value={regForm.email}
                    onChange={(e) => setRegForm({ ...regForm, email: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label>Phone Number</label>
                  <input
                    type="tel"
                    required
                    placeholder="9876543210"
                    value={regForm.phone}
                    onChange={(e) => setRegForm({ ...regForm, phone: e.target.value })}
                  />
                </div>

                <div className="form-group">
                  <label>College / Company Organization</label>
                  <input
                    type="text"
                    placeholder="e.g. VIT Chennai"
                    value={regForm.college}
                    onChange={(e) => setRegForm({ ...regForm, college: e.target.value })}
                  />
                </div>

                <div className="btn-row" style={{ marginTop: "1.5rem" }}>
                  <button type="submit" className={`btn btn-block ${isFull ? "btn-warning" : "btn-primary"}`} disabled={submitting}>
                    {submitting ? "Processing..." : isFull ? "Confirm Waitlist Entry" : "Complete Registration & Get Pass"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Ticket Pass Modal Trigger */}
      {issuedTicket && (
        <TicketPass ticket={issuedTicket} onClose={() => setIssuedTicket(null)} />
      )}
    </div>
  );
}
