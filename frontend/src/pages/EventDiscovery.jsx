import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/api";
import { useAuth } from "../context/AuthContext";

const CATEGORIES = ["All", "Technology", "Management", "Cultural", "Sports", "Workshop", "Conference", "Hackathon", "Seminar", "Leadership"];

export default function EventDiscovery() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All");
  const [filterOnline, setFilterOnline] = useState("all");
  const [sortBy, setSortBy] = useState("date");
  const { user } = useAuth();

  const loadEvents = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      if (category !== "All") params.append("category", category);
      if (filterOnline === "online") params.append("is_online", "true");
      if (filterOnline === "in_person") params.append("is_online", "false");
      params.append("sort_by", sortBy);

      const data = await api.getEvents(params.toString());
      setEvents(data);
    } catch (err) {
      console.error("Failed to load events", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, [category, filterOnline, sortBy]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    loadEvents();
  };

  return (
    <div className="discovery-container">
      {/* Hero Banner */}
      <div className="discovery-hero">
        <div className="hero-content">
          <span className="hero-tag">🌟 Premier Events Platform</span>
          <h1>Discover & Register for World-Class Events</h1>
          <p>
            Explore conferences, technical symposiums, workshops, cultural fests and hackathons.
            Secure your spot with instant digital passes.
          </p>

          {/* Search Bar */}
          <form onSubmit={handleSearchSubmit} className="hero-search-form">
            <div className="search-input-wrapper">
              <span className="search-icon">🔍</span>
              <input
                type="text"
                placeholder="Search events by title, keyword, topic, or venue..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <button type="submit" className="btn btn-primary hero-search-btn">
              Search
            </button>
          </form>
        </div>
      </div>

      {/* Filter & Category Bar */}
      <div className="filter-controls-bar">
        {/* Category Pills */}
        <div className="category-chips-row">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              className={`category-chip ${category === cat ? "active" : ""}`}
              onClick={() => setCategory(cat)}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Extra Filters */}
        <div className="discovery-subfilters">
          <div className="filter-group-inline">
            <label>Format:</label>
            <select value={filterOnline} onChange={(e) => setFilterOnline(e.target.value)}>
              <option value="all">All Formats</option>
              <option value="online">🌐 Online Live</option>
              <option value="in_person">🏛️ In-Person</option>
            </select>
          </div>

          <div className="filter-group-inline">
            <label>Sort By:</label>
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
              <option value="date">Date (Earliest)</option>
              <option value="name">Event Name</option>
              <option value="capacity">Capacity</option>
            </select>
          </div>
        </div>
      </div>

      {/* Event Cards Grid */}
      <div className="discovery-grid-section">
        <div className="section-title-row">
          <h2>Available Events ({events.length})</h2>
          {user && (
            <Link to="/my-registrations" className="btn btn-outline btn-sm">
              View My Passes ➔
            </Link>
          )}
        </div>

        {loading ? (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Finding exciting events...</p>
          </div>
        ) : events.length === 0 ? (
          <div className="empty-discovery-card">
            <div style={{ fontSize: "3rem", marginBottom: "0.5rem" }}>🎪</div>
            <h3>No events found</h3>
            <p>Try searching for a different keyword or adjusting your category filters.</p>
            <button
              className="btn btn-primary"
              onClick={() => {
                setSearch("");
                setCategory("All");
                setFilterOnline("all");
              }}
            >
              Reset All Filters
            </button>
          </div>
        ) : (
          <div className="event-cards-grid">
            {events.map((ev) => {
              const cap = ev.capacity || 100;
              const filled = ev.registered_count || 0;
              const pct = Math.min(100, Math.round((filled / cap) * 100));
              const isFull = ev.is_full;

              return (
                <div key={ev.id} className="event-card">
                  {/* Card Header & Banner */}
                  <div className="event-card-banner">
                    <div className="event-card-badges">
                      <span className="card-cat-badge">{ev.category || ev.event_type}</span>
                      {ev.is_online ? (
                        <span className="card-format-badge format-online">🌐 Online</span>
                      ) : (
                        <span className="card-format-badge format-venue">🏛️ In-Person</span>
                      )}
                    </div>
                    <div className="event-card-date-badge">
                      <span className="date-month">
                        {ev.date ? new Date(ev.date).toLocaleString("default", { month: "short" }).toUpperCase() : "TBD"}
                      </span>
                      <span className="date-day">
                        {ev.date ? ev.date.split("-")[2] : ""}
                      </span>
                    </div>
                  </div>

                  {/* Card Content */}
                  <div className="event-card-body">
                    <h3 className="event-card-title">
                      <Link to={`/events/${ev.id}`}>{ev.name}</Link>
                    </h3>

                    <p className="event-card-desc">
                      {ev.description || "Join us for an inspiring session featuring industry leaders, hands-on activities, and networking opportunities."}
                    </p>

                    <div className="event-card-meta-list">
                      <div className="meta-row">
                        <span className="meta-icon">🕒</span>
                        <span>{ev.time}</span>
                      </div>
                      <div className="meta-row">
                        <span className="meta-icon">📍</span>
                        <span>{ev.venue_name || (ev.is_online ? "Virtual Live Room" : "Venue TBA")}</span>
                      </div>
                      {ev.organizer_name && (
                        <div className="meta-row">
                          <span className="meta-icon">👤</span>
                          <span>Hosted by {ev.organizer_name}</span>
                        </div>
                      )}
                    </div>

                    {/* Capacity Progress Bar */}
                    <div className="capacity-bar-wrap">
                      <div className="capacity-labels">
                        <span>{filled} / {cap} Seats Reserved</span>
                        <strong style={{ color: isFull ? "#ef4444" : "#10b981" }}>
                          {isFull ? "Waitlist Open" : `${ev.remaining_seats} left`}
                        </strong>
                      </div>
                      <div className="progress-track">
                        <div
                          className={`progress-fill ${isFull ? "fill-full" : pct > 75 ? "fill-warn" : ""}`}
                          style={{ width: `${pct}%` }}
                        ></div>
                      </div>
                    </div>
                  </div>

                  {/* Card Footer Action */}
                  <div className="event-card-footer">
                    <Link
                      to={`/events/${ev.id}`}
                      className={`btn btn-block ${isFull ? "btn-warning" : "btn-primary"}`}
                    >
                      {isFull ? "Join Waitlist ➔" : "View Details & Register ➔"}
                    </Link>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
