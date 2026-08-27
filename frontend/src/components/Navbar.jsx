import { useState } from "react";
import { NavLink, Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useNotifications } from "../context/NotificationContext";
import "./Navbar.css";

export default function Navbar() {
  const { user, logout, isAdmin, isOrganizer } = useAuth();
  const { notifications, unreadCount, markAsRead, markAllAsRead } = useNotifications();
  const [showNotifs, setShowNotifs] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    setShowUserMenu(false);
    navigate("/login");
  };

  return (
    <header className="navbar-header">
      <nav className="navbar-container">
        {/* Brand */}
        <Link to="/" className="nav-brand" onClick={() => setMobileMenuOpen(false)}>
          <div className="brand-logo-icon">⚡</div>
          <div className="brand-text">
            <span className="brand-title">EventSphere</span>
            <span className="brand-subtitle">Enterprise ERP</span>
          </div>
        </Link>

        {/* Mobile Toggle */}
        <button
          className="mobile-toggle-btn"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle navigation"
        >
          {mobileMenuOpen ? "✕" : "☰"}
        </button>

        {/* Nav Links */}
        <div className={`nav-center-menu ${mobileMenuOpen ? "open" : ""}`}>
          <NavLink to="/explore" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")} onClick={() => setMobileMenuOpen(false)}>
            Explore
          </NavLink>

          {user && (
            <NavLink to="/my-registrations" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")} onClick={() => setMobileMenuOpen(false)}>
              My Passes
            </NavLink>
          )}

          {isOrganizer && (
            <>
              <NavLink to="/organizer" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")} onClick={() => setMobileMenuOpen(false)}>
                Organizer Workspace
              </NavLink>
              <NavLink to="/events" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")} onClick={() => setMobileMenuOpen(false)}>
                Events
              </NavLink>
              <NavLink to="/attendance" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")} onClick={() => setMobileMenuOpen(false)}>
                Check-In
              </NavLink>
            </>
          )}

          {isAdmin && (
            <>
              <NavLink to="/admin" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")} onClick={() => setMobileMenuOpen(false)}>
                Admin Portal
              </NavLink>
              <NavLink to="/analytics" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")} onClick={() => setMobileMenuOpen(false)}>
                Analytics
              </NavLink>
            </>
          )}

          {/* Operational Modules */}
          <NavLink to="/venues" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")} onClick={() => setMobileMenuOpen(false)}>
            Venues
          </NavLink>
          <NavLink to="/resources" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")} onClick={() => setMobileMenuOpen(false)}>
            Resources
          </NavLink>
          <NavLink to="/vendors" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")} onClick={() => setMobileMenuOpen(false)}>
            Vendors
          </NavLink>
          <NavLink to="/report" className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")} onClick={() => setMobileMenuOpen(false)}>
            Reports
          </NavLink>
        </div>

        {/* Nav Right (Auth & Notifications) */}
        <div className="nav-right-actions">
          {user ? (
            <>
              {/* Notification Bell */}
              <div className="notif-dropdown-wrapper">
                <button
                  className="icon-btn notif-bell-btn"
                  onClick={() => setShowNotifs(!showNotifs)}
                  title="Notifications"
                >
                  🔔
                  {unreadCount > 0 && <span className="notif-badge">{unreadCount}</span>}
                </button>

                {showNotifs && (
                  <div className="notif-dropdown-pane">
                    <div className="notif-header">
                      <strong>Notifications ({unreadCount} new)</strong>
                      {unreadCount > 0 && (
                        <button className="text-btn" onClick={markAllAsRead}>
                          Mark all read
                        </button>
                      )}
                    </div>
                    <div className="notif-list">
                      {notifications.length === 0 ? (
                        <p className="notif-empty">No notifications yet.</p>
                      ) : (
                        notifications.slice(0, 8).map((n) => (
                          <div
                            key={n.id}
                            className={`notif-item ${n.is_read ? "read" : "unread"}`}
                            onClick={() => markAsRead(n.id)}
                          >
                            <div className="notif-title">{n.title}</div>
                            <div className="notif-desc">{n.message}</div>
                            <div className="notif-time">{n.created_at?.slice(0, 16)}</div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* User Avatar Menu */}
              <div className="user-dropdown-wrapper">
                <button
                  className="user-profile-trigger"
                  onClick={() => setShowUserMenu(!showUserMenu)}
                >
                  <div className="avatar-circle">
                    {user.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="user-details-snippet">
                    <span className="user-name">{user.name}</span>
                    <span className={`role-chip role-${user.role}`}>{user.role}</span>
                  </div>
                  <span className="dropdown-caret">▾</span>
                </button>

                {showUserMenu && (
                  <div className="user-dropdown-pane">
                    <div className="user-dropdown-header">
                      <strong>{user.name}</strong>
                      <span>{user.email}</span>
                      <span className={`role-pill role-${user.role}`}>{user.role.toUpperCase()}</span>
                    </div>
                    <div className="dropdown-divider"></div>
                    <Link
                      to="/profile"
                      className="dropdown-item"
                      onClick={() => setShowUserMenu(false)}
                    >
                      👤 My Profile & Settings
                    </Link>
                    <Link
                      to="/my-registrations"
                      className="dropdown-item"
                      onClick={() => setShowUserMenu(false)}
                    >
                      🎫 My Event Passes
                    </Link>
                    {isOrganizer && (
                      <Link
                        to="/organizer"
                        className="dropdown-item"
                        onClick={() => setShowUserMenu(false)}
                      >
                        📊 Organizer Workspace
                      </Link>
                    )}
                    {isAdmin && (
                      <Link
                        to="/admin"
                        className="dropdown-item"
                        onClick={() => setShowUserMenu(false)}
                      >
                        🛡️ Admin Control Panel
                      </Link>
                    )}
                    <div className="dropdown-divider"></div>
                    <button className="dropdown-item logout-btn" onClick={handleLogout}>
                      🚪 Sign Out
                    </button>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="nav-auth-buttons">
              <Link to="/login" className="btn btn-outline">
                Sign In
              </Link>
              <Link to="/register" className="btn btn-primary">
                Register
              </Link>
            </div>
          )}
        </div>
      </nav>
    </header>
  );
}
