import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { RadioGroup, RadioGroupItem } from '../components/ui/radio-group';
import { Checkbox } from '../components/ui/checkbox';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { Input } from '../components/ui/input';
import { GraduationCap, ChevronRight, ChevronLeft, AlertCircle, CheckCircle2 } from 'lucide-react';
import api, { isAuthenticated } from '../utils/api';

const GRADUATION_TERMS = [
  'Fall 2025', 'Spring 2026', 'Summer 2026',
  'Fall 2026', 'Spring 2027', 'Summer 2027',
  'Fall 2027', 'Spring 2028', 'Summer 2028',
  'Fall 2028', 'Spring 2029', 'Summer 2029'
];

const CURRENT_SEMESTERS = [
  'Spring 2026', 'Summer 2026', 'Fall 2026'
];

export const OnboardingPage = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [options, setOptions] = useState({
    campuses: [],
    academic_levels: [],
    credit_loads: [],
    financial_aid_statuses: []
  });

  const [formData, setFormData] = useState({
    campus: '',
    major: '',
    academic_level: '',
    credit_load: '',
    financial_aid_status: '',
    international_student: false,
    expected_graduation: '',
    current_semester: 'Spring 2026'
  });

  useEffect(() => {
    fetchOptions();
    checkAuth();
  }, []);

  const checkAuth = async () => {
    if (!isAuthenticated()) {
      navigate('/login');
      return;
    }
    
    try {
      const response = await api.get('/auth/me');
      if (response.data.profile_complete) {
        navigate('/assistant');
      }
    } catch (err) {
      navigate('/login');
    }
  };

  const fetchOptions = async () => {
    try {
      const response = await api.get('/user/profile-options');
      setOptions(response.data);
    } catch (err) {
      console.error('Failed to fetch options:', err);
    }
  };

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setError('');
  };

  const validateStep = () => {
    switch (step) {
      case 1:
        if (!formData.campus || !formData.major) {
          setError('Please complete all fields');
          return false;
        }
        break;
      case 2:
        if (!formData.academic_level || !formData.credit_load) {
          setError('Please complete all fields');
          return false;
        }
        break;
      case 3:
        if (!formData.financial_aid_status || !formData.expected_graduation) {
          setError('Please complete all fields');
          return false;
        }
        break;
    }
    return true;
  };

  const nextStep = () => {
    if (validateStep()) {
      setStep(prev => prev + 1);
    }
  };

  const prevStep = () => {
    setStep(prev => prev - 1);
    setError('');
  };

  const handleSubmit = async () => {
    if (!validateStep()) return;

    setIsLoading(true);
    setError('');

    try {
      await api.post('/user/profile', formData);
      navigate('/assistant');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save profile. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const totalSteps = 3;
  const progress = (step / totalSteps) * 100;

  return (
    <div 
      className="min-h-screen flex items-center justify-center p-6 bg-[#F4F6F8]"
      data-testid="onboarding-page"
    >
      <div className="w-full max-w-lg">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="w-10 h-10 bg-[#001E44] rounded-xl flex items-center justify-center">
              <GraduationCap className="w-6 h-6 text-white" />
            </div>
            <span className="font-heading font-bold text-xl text-[#001E44]">ACE</span>
          </div>
          <h1 className="text-2xl font-heading font-bold text-[#001E44] mb-2">
            Complete Your Profile
          </h1>
          <p className="text-sm text-[#475569]">
            This helps ACE provide personalized academic guidance
          </p>
        </div>

        {/* Progress bar */}
        <div className="mb-6">
          <div className="flex justify-between text-xs text-[#475569] mb-2">
            <span>Step {step} of {totalSteps}</span>
            <span>{Math.round(progress)}% complete</span>
          </div>
          <div className="h-2 bg-[#E2E8F0] rounded-full overflow-hidden">
            <div 
              className="h-full bg-[#001E44] transition-all duration-300 rounded-full"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        <Card className="border-0 shadow-lg">
          <CardContent className="p-6">
            {/* Error */}
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-sm text-red-700">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                {error}
              </div>
            )}

            {/* Step 1: Campus & Major */}
            {step === 1 && (
              <div className="space-y-6" data-testid="step-1">
                <div>
                  <CardTitle className="text-lg mb-1">Campus & Major</CardTitle>
                  <CardDescription>Where are you studying?</CardDescription>
                </div>

                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="campus">Campus</Label>
                    <Select 
                      value={formData.campus} 
                      onValueChange={(v) => handleChange('campus', v)}
                    >
                      <SelectTrigger data-testid="campus-select">
                        <SelectValue placeholder="Select your campus" />
                      </SelectTrigger>
                      <SelectContent>
                        {options.campuses.map(campus => (
                          <SelectItem key={campus} value={campus}>{campus}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="major">Major</Label>
                    <Input
                      id="major"
                      placeholder="e.g., Computer Science"
                      value={formData.major}
                      onChange={(e) => handleChange('major', e.target.value)}
                      data-testid="major-input"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Academic Standing */}
            {step === 2 && (
              <div className="space-y-6" data-testid="step-2">
                <div>
                  <CardTitle className="text-lg mb-1">Academic Standing</CardTitle>
                  <CardDescription>Tell us about your current enrollment</CardDescription>
                </div>

                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label>Academic Level</Label>
                    <RadioGroup 
                      value={formData.academic_level}
                      onValueChange={(v) => handleChange('academic_level', v)}
                      className="grid grid-cols-2 gap-2"
                    >
                      {options.academic_levels.map(level => (
                        <div key={level} className="flex items-center space-x-2">
                          <RadioGroupItem 
                            value={level} 
                            id={level}
                            data-testid={`level-${level.split(' ')[0].toLowerCase()}`}
                          />
                          <Label htmlFor={level} className="text-sm font-normal cursor-pointer">
                            {level}
                          </Label>
                        </div>
                      ))}
                    </RadioGroup>
                  </div>

                  <div className="space-y-2">
                    <Label>Credit Load</Label>
                    <RadioGroup 
                      value={formData.credit_load}
                      onValueChange={(v) => handleChange('credit_load', v)}
                      className="space-y-2"
                    >
                      {options.credit_loads.map(load => (
                        <div key={load} className="flex items-center space-x-2">
                          <RadioGroupItem 
                            value={load} 
                            id={load}
                            data-testid={`load-${load.split(' ')[0].toLowerCase()}`}
                          />
                          <Label htmlFor={load} className="text-sm font-normal cursor-pointer">
                            {load}
                          </Label>
                        </div>
                      ))}
                    </RadioGroup>
                  </div>

                  <div className="space-y-2">
                    <Label>Current Semester</Label>
                    <Select 
                      value={formData.current_semester} 
                      onValueChange={(v) => handleChange('current_semester', v)}
                    >
                      <SelectTrigger data-testid="semester-select">
                        <SelectValue placeholder="Select current semester" />
                      </SelectTrigger>
                      <SelectContent>
                        {CURRENT_SEMESTERS.map(sem => (
                          <SelectItem key={sem} value={sem}>{sem}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            )}

            {/* Step 3: Financial & Status */}
            {step === 3 && (
              <div className="space-y-6" data-testid="step-3">
                <div>
                  <CardTitle className="text-lg mb-1">Additional Information</CardTitle>
                  <CardDescription>Help us understand your situation better</CardDescription>
                </div>

                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label>Financial Aid Status</Label>
                    <Select 
                      value={formData.financial_aid_status} 
                      onValueChange={(v) => handleChange('financial_aid_status', v)}
                    >
                      <SelectTrigger data-testid="aid-select">
                        <SelectValue placeholder="Select your status" />
                      </SelectTrigger>
                      <SelectContent>
                        {options.financial_aid_statuses.map(status => (
                          <SelectItem key={status} value={status}>{status}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Expected Graduation</Label>
                    <Select 
                      value={formData.expected_graduation} 
                      onValueChange={(v) => handleChange('expected_graduation', v)}
                    >
                      <SelectTrigger data-testid="graduation-select">
                        <SelectValue placeholder="Select graduation term" />
                      </SelectTrigger>
                      <SelectContent>
                        {GRADUATION_TERMS.map(term => (
                          <SelectItem key={term} value={term}>{term}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex items-center space-x-3 p-3 bg-[#F8FAFC] rounded-lg border border-[#E2E8F0]">
                    <Checkbox
                      id="international"
                      checked={formData.international_student}
                      onCheckedChange={(checked) => handleChange('international_student', checked)}
                      data-testid="international-checkbox"
                    />
                    <div>
                      <Label htmlFor="international" className="text-sm font-medium cursor-pointer">
                        I am an international student
                      </Label>
                      <p className="text-xs text-[#475569] mt-0.5">
                        This helps ACE provide visa-related guidance
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Navigation */}
            <div className="flex justify-between mt-8 pt-4 border-t border-[#E2E8F0]">
              {step > 1 ? (
                <Button
                  variant="outline"
                  onClick={prevStep}
                  className="gap-2"
                  data-testid="prev-button"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Back
                </Button>
              ) : (
                <div />
              )}

              {step < totalSteps ? (
                <Button
                  onClick={nextStep}
                  className="bg-[#001E44] hover:bg-[#1E407C] gap-2"
                  data-testid="next-button"
                >
                  Continue
                  <ChevronRight className="w-4 h-4" />
                </Button>
              ) : (
                <Button
                  onClick={handleSubmit}
                  disabled={isLoading}
                  className="bg-[#001E44] hover:bg-[#1E407C] gap-2"
                  data-testid="submit-button"
                >
                  {isLoading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-4 h-4" />
                      Complete Setup
                    </>
                  )}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Disclaimer */}
        <p className="text-[10px] text-[#94A3B8] text-center mt-6 px-4">
          ACE is a decision-support beta tool and not an official PSU advising service. 
          Your profile information is used only to personalize guidance.
        </p>
      </div>
    </div>
  );
};

export default OnboardingPage;
