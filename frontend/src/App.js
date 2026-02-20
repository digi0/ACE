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
import api, { isAuthenticated, getStoredUser } from './utils/api';

// Protected route wrapper - verifies auth with server
const ProtectedRoute = ({ children, requireProfile = true }) => {
  const navigate = useNavigate();
  const [authState, setAuthState] = useState({ loading: true, valid: false });

  useEffect(() => {
    const checkAuth = async () => {
      if (!isAuthenticated()) {
        navigate('/login', { replace: true });
        return;
      }

      try {
        const response = await api.get('/auth/me');
        const { profile_complete } = response.data;
        
        if (requireProfile && !profile_complete) {
          navigate('/onboarding', { replace: true });
          return;
        }
        
        setAuthState({ loading: false, valid: true });
      } catch (error) {
        navigate('/login', { replace: true });
      }
    };

    checkAuth();
  }, [navigate, requireProfile]);

  if (authState.loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F4F6F8]">
        <div className="w-10 h-10 border-4 border-[#001E44] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!authState.valid) {
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
      if (!isAuthenticated()) {
        setChecked(true);
        return;
      }

      try {
        const response = await api.get('/auth/me');
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
