import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { GraduationCap, Shield, BookOpen, Users } from 'lucide-react';

export const LoginPage = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(false);

  const handleLogin = async () => {
    setIsLoading(true);
    // Simulate SSO login delay
    setTimeout(() => {
      // Store mocked auth state
      localStorage.setItem('ace_authenticated', 'true');
      localStorage.setItem('ace_student_id', 'abc123456');
      navigate('/assistant');
    }, 800);
  };

  return (
    <div 
      className="min-h-screen flex items-center justify-center p-8 relative"
      data-testid="login-page"
    >
      {/* Background with subtle overlay */}
      <div 
        className="absolute inset-0 bg-cover bg-center"
        style={{
          backgroundImage: `url('https://images.unsplash.com/photo-1724157934664-86b93f93858b?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NTJ8MHwxfHNlYXJjaHwxfHx1bml2ZXJzaXR5JTIwY2FtcHVzJTIwbGlicmFyeSUyMHN0dWRlbnRzfGVufDB8fHx8MTc2OTg2MzY5MHww&ixlib=rb-4.1.0&q=85')`
        }}
      />
      <div className="absolute inset-0 bg-gradient-to-br from-[#001E44]/90 via-[#001E44]/80 to-[#1E407C]/70" />
      
      {/* Content */}
      <div className="relative z-10 w-full max-w-md">
        <Card className="bg-white/95 backdrop-blur-sm border-0 shadow-2xl">
          <CardContent className="p-8">
            {/* Logo & Branding */}
            <div className="text-center mb-8">
              <div className="flex items-center justify-center gap-3 mb-4">
                <div className="w-12 h-12 bg-[#001E44] rounded-xl flex items-center justify-center">
                  <GraduationCap className="w-7 h-7 text-white" />
                </div>
                <div className="text-left">
                  <h1 className="font-heading text-2xl font-bold text-[#001E44]">ACE</h1>
                  <p className="text-xs text-[#475569] tracking-wide">Academic Clarity Engine</p>
                </div>
              </div>
              <p className="text-[#475569] text-sm leading-relaxed">
                Your personal academic advisor for navigating Penn State
              </p>
            </div>

            {/* Penn State SSO Button */}
            <Button
              onClick={handleLogin}
              disabled={isLoading}
              className="w-full h-12 bg-[#001E44] hover:bg-[#1E407C] text-white font-medium rounded-lg transition-all duration-200 shadow-md hover:shadow-lg"
              data-testid="psu-login-button"
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Signing in...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Shield className="w-5 h-5" />
                  Sign in with Penn State
                </span>
              )}
            </Button>

            {/* Info note */}
            <p className="text-center text-xs text-[#94A3B8] mt-4">
              Use your Penn State credentials to access ACE
            </p>

            {/* Feature highlights */}
            <div className="mt-8 pt-6 border-t border-[#E2E8F0]">
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="w-10 h-10 mx-auto mb-2 bg-[#96BEE6]/20 rounded-lg flex items-center justify-center">
                    <BookOpen className="w-5 h-5 text-[#001E44]" />
                  </div>
                  <p className="text-xs text-[#475569]">Policy Guidance</p>
                </div>
                <div className="text-center">
                  <div className="w-10 h-10 mx-auto mb-2 bg-[#96BEE6]/20 rounded-lg flex items-center justify-center">
                    <Users className="w-5 h-5 text-[#001E44]" />
                  </div>
                  <p className="text-xs text-[#475569]">Personalized Help</p>
                </div>
                <div className="text-center">
                  <div className="w-10 h-10 mx-auto mb-2 bg-[#96BEE6]/20 rounded-lg flex items-center justify-center">
                    <Shield className="w-5 h-5 text-[#001E44]" />
                  </div>
                  <p className="text-xs text-[#475569]">Trusted Sources</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-xs text-white/60 mt-6">
          © 2026 Penn State University · ACE is an academic support tool
        </p>
      </div>
    </div>
  );
};

export default LoginPage;
