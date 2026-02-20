import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { ScrollArea } from '../components/ui/scroll-area';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select';
import { 
  GraduationCap, 
  Plus, 
  Pencil, 
  Trash2, 
  ArrowLeft,
  AlertCircle,
  CheckCircle2,
  ExternalLink,
  Calendar
} from 'lucide-react';
import api, { isAuthenticated } from '../utils/api';

const RISK_CATEGORIES = ['low', 'medium', 'high'];
const POLICY_CATEGORIES = [
  'academic_calendar', 'withdrawal', 'tuition', 'grades', 
  'advising', 'academic_standing', 'registration', 
  'financial_aid', 'international', 'graduation', 'enrollment'
];

export const AdminPage = () => {
  const navigate = useNavigate();
  const [policies, setPolicies] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [editingPolicy, setEditingPolicy] = useState(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [formData, setFormData] = useState({
    vault_id: '',
    title: '',
    summary: '',
    category: '',
    tags: '',
    risk_category: 'low',
    content: '',
    source_link: ''
  });

  useEffect(() => {
    checkAdminAccess();
    fetchPolicies();
  }, []);

  const checkAdminAccess = async () => {
    if (!isAuthenticated()) {
      navigate('/login');
      return;
    }
    
    try {
      const response = await api.get('/auth/me');
      if (!response.data.is_admin) {
        navigate('/assistant');
      }
    } catch (err) {
      navigate('/login');
    }
  };

  const fetchPolicies = async () => {
    try {
      const response = await api.get('/admin/policies');
      setPolicies(response.data);
    } catch (err) {
      setError('Failed to load policies');
    } finally {
      setIsLoading(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const openEditDialog = (policy) => {
    setEditingPolicy(policy);
    setFormData({
      vault_id: policy.vault_id,
      title: policy.title,
      summary: policy.summary,
      category: policy.category,
      tags: policy.tags.join(', '),
      risk_category: policy.risk_category,
      content: policy.content,
      source_link: policy.source_link
    });
    setIsDialogOpen(true);
  };

  const openNewDialog = () => {
    setEditingPolicy(null);
    setFormData({
      vault_id: '',
      title: '',
      summary: '',
      category: '',
      tags: '',
      risk_category: 'low',
      content: '',
      source_link: ''
    });
    setIsDialogOpen(true);
  };

  const handleSubmit = async () => {
    setError('');
    setSuccess('');

    const payload = {
      ...formData,
      tags: formData.tags.split(',').map(t => t.trim()).filter(Boolean)
    };

    try {
      if (editingPolicy) {
        await axios.put(`${API}/admin/policies/${editingPolicy.vault_id}`, payload, { 
          withCredentials: true 
        });
        setSuccess('Policy updated successfully');
      } else {
        await axios.post(`${API}/admin/policies`, payload, { 
          withCredentials: true 
        });
        setSuccess('Policy added successfully');
      }
      
      fetchPolicies();
      setIsDialogOpen(false);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save policy');
    }
  };

  const handleDelete = async (vaultId) => {
    if (!window.confirm('Are you sure you want to delete this policy?')) return;

    try {
      await axios.delete(`${API}/admin/policies/${vaultId}`, { withCredentials: true });
      setSuccess('Policy deleted');
      fetchPolicies();
    } catch (err) {
      setError('Failed to delete policy');
    }
  };

  const getRiskColor = (risk) => {
    switch (risk) {
      case 'high': return 'bg-red-100 text-red-700 border-red-200';
      case 'medium': return 'bg-amber-100 text-amber-700 border-amber-200';
      default: return 'bg-emerald-100 text-emerald-700 border-emerald-200';
    }
  };

  return (
    <div className="min-h-screen bg-[#F4F6F8]" data-testid="admin-page">
      {/* Header */}
      <header className="bg-white border-b border-[#E2E8F0] px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate('/assistant')}
              className="text-[#475569]"
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-[#001E44] rounded-lg flex items-center justify-center">
                <GraduationCap className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="font-heading font-bold text-[#001E44]">ACE Admin</h1>
                <p className="text-xs text-[#475569]">Policy Vault Management</p>
              </div>
            </div>
          </div>

          <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
            <DialogTrigger asChild>
              <Button 
                onClick={openNewDialog}
                className="bg-[#001E44] hover:bg-[#1E407C] gap-2"
                data-testid="add-policy-button"
              >
                <Plus className="w-4 h-4" />
                Add Policy
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="font-heading">
                  {editingPolicy ? 'Edit Policy' : 'Add New Policy'}
                </DialogTitle>
              </DialogHeader>
              
              <div className="space-y-4 py-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Vault ID</Label>
                    <Input
                      value={formData.vault_id}
                      onChange={(e) => handleChange('vault_id', e.target.value)}
                      placeholder="PSU-XXX-001"
                      disabled={!!editingPolicy}
                      data-testid="vault-id-input"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Category</Label>
                    <Select 
                      value={formData.category}
                      onValueChange={(v) => handleChange('category', v)}
                    >
                      <SelectTrigger data-testid="category-select">
                        <SelectValue placeholder="Select category" />
                      </SelectTrigger>
                      <SelectContent>
                        {POLICY_CATEGORIES.map(cat => (
                          <SelectItem key={cat} value={cat}>
                            {cat.replace('_', ' ')}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Title</Label>
                  <Input
                    value={formData.title}
                    onChange={(e) => handleChange('title', e.target.value)}
                    placeholder="Policy title"
                    data-testid="title-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Summary</Label>
                  <Textarea
                    value={formData.summary}
                    onChange={(e) => handleChange('summary', e.target.value)}
                    placeholder="Brief summary of the policy"
                    rows={2}
                    data-testid="summary-input"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Full Content</Label>
                  <Textarea
                    value={formData.content}
                    onChange={(e) => handleChange('content', e.target.value)}
                    placeholder="Detailed policy content"
                    rows={4}
                    data-testid="content-input"
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Risk Category</Label>
                    <Select 
                      value={formData.risk_category}
                      onValueChange={(v) => handleChange('risk_category', v)}
                    >
                      <SelectTrigger data-testid="risk-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {RISK_CATEGORIES.map(risk => (
                          <SelectItem key={risk} value={risk}>
                            {risk.charAt(0).toUpperCase() + risk.slice(1)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Tags (comma-separated)</Label>
                    <Input
                      value={formData.tags}
                      onChange={(e) => handleChange('tags', e.target.value)}
                      placeholder="deadline, withdrawal, grades"
                      data-testid="tags-input"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Source Link</Label>
                  <Input
                    value={formData.source_link}
                    onChange={(e) => handleChange('source_link', e.target.value)}
                    placeholder="https://registrar.psu.edu/..."
                    data-testid="source-link-input"
                  />
                </div>

                {error && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-sm text-red-700">
                    <AlertCircle className="w-4 h-4" />
                    {error}
                  </div>
                )}

                <div className="flex justify-end gap-2 pt-4">
                  <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button 
                    onClick={handleSubmit}
                    className="bg-[#001E44] hover:bg-[#1E407C]"
                    data-testid="save-policy-button"
                  >
                    {editingPolicy ? 'Update Policy' : 'Add Policy'}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-6xl mx-auto p-6">
        {/* Messages */}
        {success && (
          <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2 text-sm text-emerald-700">
            <CheckCircle2 className="w-4 h-4" />
            {success}
          </div>
        )}

        {error && !isDialogOpen && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-sm text-red-700">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}

        {/* Policies Grid */}
        {isLoading ? (
          <div className="grid gap-4 md:grid-cols-2">
            {[1, 2, 3, 4].map(i => (
              <div key={i} className="h-48 bg-white rounded-xl animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {policies.map(policy => (
              <Card key={policy.vault_id} className="border-0 shadow-sm hover:shadow-md transition-shadow">
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xs font-mono text-[#94A3B8] mb-1">{policy.vault_id}</p>
                      <CardTitle className="text-base">{policy.title}</CardTitle>
                    </div>
                    <Badge className={`${getRiskColor(policy.risk_category)} text-xs`}>
                      {policy.risk_category}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-[#475569] line-clamp-2 mb-3">
                    {policy.summary}
                  </p>
                  
                  <div className="flex flex-wrap gap-1 mb-3">
                    {policy.tags?.slice(0, 4).map(tag => (
                      <span 
                        key={tag} 
                        className="px-2 py-0.5 bg-[#F1F5F9] text-[#475569] text-xs rounded"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>

                  <div className="flex items-center justify-between pt-3 border-t border-[#E2E8F0]">
                    <div className="flex items-center gap-1 text-xs text-[#94A3B8]">
                      <Calendar className="w-3 h-3" />
                      {policy.last_reviewed}
                    </div>
                    <div className="flex items-center gap-1">
                      <a 
                        href={policy.source_link} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="p-2 text-[#475569] hover:bg-[#F1F5F9] rounded-md transition-colors"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => openEditDialog(policy)}
                        className="h-8 w-8"
                        data-testid={`edit-${policy.vault_id}`}
                      >
                        <Pencil className="w-4 h-4 text-[#475569]" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => handleDelete(policy.vault_id)}
                        className="h-8 w-8"
                        data-testid={`delete-${policy.vault_id}`}
                      >
                        <Trash2 className="w-4 h-4 text-red-500" />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default AdminPage;
