import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { api } from "../api/api";

export default function Profile() {
  const { user, updateProfile } = useAuth();
  const [profileForm, setProfileForm] = useState({
    name: user?.name || "",
    phone: user?.phone || "",
    organization: user?.organization || "",
    avatar_url: user?.avatar_url || "",
  });
  const [pwdForm, setPwdForm] = useState({ old_password: "", new_password: "" });
  const [msg, setMsg] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [loadingPwd, setLoadingPwd] = useState(false);

  const flash = (text, type = "success") => {
    setMsg({ text, type });
    setTimeout(() => setMsg(null), 4000);
  };

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setLoadingProfile(true);
    try {
      const res = await api.updateProfile(profileForm);
      updateProfile(res.user);
      flash("Profile updated successfully!");
    } catch (err) {
      flash(err.message || "Failed to update profile", "error");
    } finally {
      setLoadingProfile(false);
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setLoadingPwd(true);
    try {
      const res = await api.changePassword(pwdForm);
      flash(res.message || "Password changed successfully!");
      setPwdForm({ old_password: "", new_password: "" });
    } catch (err) {
      flash(err.message || "Failed to change password", "error");
    } finally {
      setLoadingPwd(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <h1>Account Profile & Security</h1>
        <p>Manage your personal information, organization details and login credentials</p>
      </div>

      {msg && <div className={`alert alert-${msg.type}`}>{msg.text}</div>}

      <div className="profile-layout-grid">
        {/* Profile Card Summary */}
        <div className="card profile-summary-card">
          <div className="profile-avatar-large">
            {user?.name?.charAt(0).toUpperCase()}
          </div>
          <h3>{user?.name}</h3>
          <p className="profile-email">{user?.email}</p>
          <span className={`role-badge-large role-${user?.role}`}>
            {user?.role?.toUpperCase()}
          </span>

          <div className="profile-meta-list">
            <div className="meta-item">
              <span>Organization</span>
              <strong>{user?.organization || "None"}</strong>
            </div>
            <div className="meta-item">
              <span>Contact Phone</span>
              <strong>{user?.phone || "Not set"}</strong>
            </div>
            <div className="meta-item">
              <span>Account Status</span>
              <strong style={{ color: "#10b981" }}>Active & Verified</strong>
            </div>
          </div>
        </div>

        {/* Profile Edit Form */}
        <div className="card">
          <h2>Update Personal Information</h2>
          <form onSubmit={handleUpdateProfile}>
            <div className="form-grid">
              <div className="form-group" style={{ gridColumn: "span 2" }}>
                <label>Full Name</label>
                <input
                  type="text"
                  required
                  value={profileForm.name}
                  onChange={(e) => setProfileForm({ ...profileForm, name: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>Phone Number</label>
                <input
                  type="text"
                  value={profileForm.phone}
                  onChange={(e) => setProfileForm({ ...profileForm, phone: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>College / Organization</label>
                <input
                  type="text"
                  value={profileForm.organization}
                  onChange={(e) => setProfileForm({ ...profileForm, organization: e.target.value })}
                />
              </div>
            </div>
            <div className="btn-row">
              <button type="submit" className="btn btn-primary" disabled={loadingProfile}>
                {loadingProfile ? "Saving..." : "Save Profile Changes"}
              </button>
            </div>
          </form>

          <div className="section-separator"></div>

          {/* Change Password */}
          <h2>Change Account Password</h2>
          <form onSubmit={handleChangePassword}>
            <div className="form-grid">
              <div className="form-group">
                <label>Current Password</label>
                <input
                  type="password"
                  required
                  value={pwdForm.old_password}
                  onChange={(e) => setPwdForm({ ...pwdForm, old_password: e.target.value })}
                />
              </div>
              <div className="form-group">
                <label>New Password (min 6 chars)</label>
                <input
                  type="password"
                  required
                  minLength={6}
                  value={pwdForm.new_password}
                  onChange={(e) => setPwdForm({ ...pwdForm, new_password: e.target.value })}
                />
              </div>
            </div>
            <div className="btn-row">
              <button type="submit" className="btn btn-warning" disabled={loadingPwd}>
                {loadingPwd ? "Updating..." : "Change Password"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
