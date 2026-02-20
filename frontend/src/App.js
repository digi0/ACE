import { useState, useEffect } from 'react';
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import { Toaster } from "./components/ui/sonner";
import { LoginPage } from "./pages/LoginPage";
import { SignupPage } from "./pages/SignupPage";
import { AuthCallback } from "./pages/AuthCallback";
import { OnboardingPage } from "./pages/OnboardingPage";
import { MainAssistant } from "./pages/MainAssistant";
import { AdminPage } from "./pages/AdminPage";
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Protected route wrapper - verifies auth server-side
const ProtectedRoute = ({ children, requireProfile = true }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isAuthenticated, setIsAuthenticated] = useState(location.state?.user ? true : null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Skip if user data passed from AuthCallback
    if (location.state?.user) {
      setIsAuthenticated(true);
      setIsLoading(false);
      return;
    }

    const checkAuth = async () => {
      try {
        const response = await axios.get(`${API}/auth/me`, { withCredentials: true });
        const { profile_complete } = response.data;
        
        if (requireProfile && !profile_complete) {
          navigate('/onboarding', { replace: true });
          return;
        }
        
        setIsAuthenticated(true);
      } catch (error) {
        setIsAuthenticated(false);
        navigate('/login', { replace: true });
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, [navigate, location.state, requireProfile]);

  if (isLoading || isAuthenticated === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F4F6F8]">
        <div className="w-10 h-10 border-4 border-[#001E44] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return children;
};

// Public route - redirects to assistant if already authenticated
const PublicRoute = ({ children }) => {
  const navigate = useNavigate();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await axios.get(`${API}/auth/me`, { withCredentials: true });
        if (response.data.profile_complete) {
          navigate('/assistant', { replace: true });
        } else {
          navigate('/onboarding', { replace: true });
        }
      } catch {
        setChecked(true);
      }
    };

    checkAuth();
  }, [navigate]);

  if (!checked) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F4F6F8]">
        <div className="w-10 h-10 border-4 border-[#001E44] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return children;
};

// App router with session_id detection
function AppRouter() {
  const location = useLocation();

  // Check URL fragment for session_id (OAuth callback)
  // This must happen synchronously during render, not in useEffect
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
      <Route path="/signup" element={<PublicRoute><SignupPage /></PublicRoute>} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      
      {/* Onboarding - requires auth but not profile */}
      <Route 
        path="/onboarding" 
        element={
          <ProtectedRoute requireProfile={false}>
            <OnboardingPage />
          </ProtectedRoute>
        } 
      />
      
      {/* Protected routes - require auth and complete profile */}
      <Route 
        path="/assistant" 
        element={
          <ProtectedRoute>
            <MainAssistant />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/admin" 
        element={
          <ProtectedRoute>
            <AdminPage />
          </ProtectedRoute>
        } 
      />
      
      {/* Default redirects */}
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AppRouter />
      </BrowserRouter>
      <Toaster position="top-right" />
    </div>
  );
}

export default App;
