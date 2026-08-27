import { createContext, useContext, useState, useEffect } from "react";
import { api } from "../api/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem("eventsphere_user");
    return saved ? JSON.parse(saved) : null;
  });
  const [token, setToken] = useState(() => localStorage.getItem("eventsphere_token"));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      api.getMe()
        .then((res) => {
          setUser(res.user);
          localStorage.setItem("eventsphere_user", JSON.stringify(res.user));
        })
        .catch(() => {
          logout();
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [token]);

  const login = (userData, userToken) => {
    setUser(userData);
    setToken(userToken);
    localStorage.setItem("eventsphere_user", JSON.stringify(userData));
    localStorage.setItem("eventsphere_token", userToken);
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    localStorage.removeItem("eventsphere_user");
    localStorage.removeItem("eventsphere_token");
  };

  const updateProfile = (updatedUser) => {
    setUser(updatedUser);
    localStorage.setItem("eventsphere_user", JSON.stringify(updatedUser));
  };

  const isAdmin = user?.role === "admin";
  const isOrganizer = user?.role === "organizer" || user?.role === "admin";
  const isParticipant = user?.role === "participant";

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        logout,
        updateProfile,
        isAdmin,
        isOrganizer,
        isParticipant,
        hasRole: (roles) => user && roles.includes(user.role),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
