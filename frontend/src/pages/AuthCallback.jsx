import { useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import api, { setAuth } from '../utils/api';

export const AuthCallback = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processAuth = async () => {
      try {
        // Extract session_id from URL fragment
        const hash = location.hash;
        const params = new URLSearchParams(hash.replace('#', ''));
        const sessionId = params.get('session_id');

        if (!sessionId) {
          console.error('No session_id in URL');
          navigate('/login');
          return;
        }

        // Exchange session_id for session token
        const response = await api.post('/auth/session', {
          session_id: sessionId
        });

        const { session_token, profile_complete, ...user } = response.data;
        setAuth(session_token, user);

        // Clear URL fragment and navigate
        window.history.replaceState({}, document.title, window.location.pathname);
        
        if (profile_complete) {
          navigate('/assistant', { replace: true });
        } else {
          navigate('/onboarding', { replace: true });
        }
      } catch (error) {
        console.error('Auth callback error:', error);
        navigate('/login', { replace: true });
      }
    };

    processAuth();
  }, [location, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F4F6F8]">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-[#001E44] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-[#475569]">Completing sign in...</p>
      </div>
    </div>
  );
};

export default AuthCallback;
