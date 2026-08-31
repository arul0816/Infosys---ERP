import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { NotificationProvider } from "./context/NotificationContext";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";

// Pages
import EventDiscovery    from "./pages/EventDiscovery";
import EventDetail       from "./pages/EventDetail";
import Login             from "./pages/Login";
import Register          from "./pages/Register";
import Profile           from "./pages/Profile";
import MyRegistrations   from "./pages/MyRegistrations";
import OrganizerDashboard from "./pages/OrganizerDashboard";
import FinanceDashboard  from "./pages/FinanceDashboard";
import AdminDashboard    from "./pages/AdminDashboard";
import Analytics         from "./pages/Analytics";
import Events            from "./pages/Events";
import Registration      from "./pages/Registration";
import Attendance        from "./pages/Attendance";
import Venues            from "./pages/Venues";
import Resources         from "./pages/Resources";
import Vendors           from "./pages/Vendors";
import Report            from "./pages/Report";

import "./App.css";

export default function App() {
  return (
    <AuthProvider>
      <NotificationProvider>
        <BrowserRouter>
          <div className="app-layout">
            <Navbar />
            <main className="main-content">
              <Routes>
                {/* Public Discovery Routes */}
                <Route path="/" element={<Navigate to="/explore" replace />} />
                <Route path="/explore" element={<EventDiscovery />} />
                <Route path="/events/:id" element={<EventDetail />} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />

                {/* Operations Directory Routes */}
                <Route path="/venues" element={
                    <ProtectedRoute allowedRoles={["admin", "organizer"]}>
                      <Venues />
                    </ProtectedRoute>
                  } />
                <Route path="/resources" element={
                    <ProtectedRoute allowedRoles={["admin", "organizer"]}>
                      <Resources />
                    </ProtectedRoute>
                  } />
                <Route path="/vendors" element={
                    <ProtectedRoute allowedRoles={["admin", "organizer"]}>
                      <Vendors />
                    </ProtectedRoute>
                  } />
                <Route path="/report" element={
                    <ProtectedRoute allowedRoles={["admin", "organizer"]}>
                      <Report />
                    </ProtectedRoute>
                  } />

                {/* Authenticated Participant Routes */}
                <Route
                  path="/my-registrations"
                  element={
                    <ProtectedRoute>
                      <MyRegistrations />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/profile"
                  element={
                    <ProtectedRoute>
                      <Profile />
                    </ProtectedRoute>
                  }
                />

                {/* Organizer & Admin Workspaces */}
                <Route
                  path="/organizer"
                  element={
                    <ProtectedRoute allowedRoles={["admin", "organizer"]}>
                      <OrganizerDashboard />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/finance"
                  element={
                    <ProtectedRoute allowedRoles={["admin", "organizer"]}>
                      <FinanceDashboard />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/events"
                  element={
                    <ProtectedRoute allowedRoles={["admin", "organizer"]}>
                      <Events />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/registration"
                  element={
                    <ProtectedRoute allowedRoles={["admin", "organizer"]}>
                      <Registration />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/attendance"
                  element={
                    <ProtectedRoute allowedRoles={["admin", "organizer"]}>
                      <Attendance />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/analytics"
                  element={
                    <ProtectedRoute allowedRoles={["admin", "organizer"]}>
                      <Analytics />
                    </ProtectedRoute>
                  }
                />

                {/* Admin-Only Control Center */}
                <Route
                  path="/admin"
                  element={
                    <ProtectedRoute allowedRoles={["admin"]}>
                      <AdminDashboard />
                    </ProtectedRoute>
                  }
                />

                {/* Fallback */}
                <Route path="*" element={<Navigate to="/explore" replace />} />
              </Routes>
            </main>
          </div>
        </BrowserRouter>
      </NotificationProvider>
    </AuthProvider>
  );
}
