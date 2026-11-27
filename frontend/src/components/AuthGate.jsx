import { useState, useEffect } from "react";
import { fetchCurrentUser, logout, AUTH_EXPIRED_EVENT } from "../api";
import LoginPage from "./LoginPage";
import "../App.css";

export default function AuthGate({ page: Page }) {
  // null while checking, then true or false
  const [signedIn, setSignedIn] = useState(null);

  useEffect(() => {
    const signOut = () => setSignedIn(false);
    window.addEventListener(AUTH_EXPIRED_EVENT, signOut);
    fetchCurrentUser().then(() => setSignedIn(true), signOut);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, signOut);
  }, []);

  async function handleLogout() {
    try {
      await logout();
    } finally {
      setSignedIn(false);
    }
  }

  if (signedIn === null) return null;
  if (!signedIn) return <LoginPage onLogin={() => setSignedIn(true)} />;
  return <Page onLogout={handleLogout} />;
}
