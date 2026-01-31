import { useState } from 'react';
import { Card, CardContent } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from './ui/collapsible';
import { 
  ChevronDown, 
  ExternalLink, 
  AlertTriangle, 
  CheckCircle2,
  AlertCircle,
  Calendar
} from 'lucide-react';

export const ACEResponse = ({ response }) => {
  const [sourcesOpen, setSourcesOpen] = useState(false);

  if (!response) return null;

  const {
    direct_answer,
    next_steps = [],
    sources_used = [],
    risk_level = 'low',
    advisor_needed = false,
    clarifying_question
  } = response;

  const getRiskConfig = (level) => {
    switch (level) {
      case 'high':
        return {
          color: 'bg-red-50 text-red-700 border-red-200',
          icon: <AlertTriangle className="w-3.5 h-3.5" />,
          label: 'High Priority'
        };
      case 'medium':
        return {
          color: 'bg-amber-50 text-amber-700 border-amber-200',
          icon: <AlertCircle className="w-3.5 h-3.5" />,
          label: 'Needs Attention'
        };
      default:
        return {
          color: 'bg-emerald-50 text-emerald-700 border-emerald-200',
          icon: <CheckCircle2 className="w-3.5 h-3.5" />,
          label: 'All Clear'
        };
    }
  };

  const riskConfig = getRiskConfig(risk_level);

  // If there's a clarifying question, show it prominently
  if (clarifying_question) {
    return (
      <Card className="bg-white border border-[#E2E8F0] shadow-sm" data-testid="ace-clarifying-response">
        <CardContent className="p-5">
          <p className="text-[#0F172A] leading-relaxed">{clarifying_question}</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card 
      className="bg-white border border-[#E2E8F0] shadow-sm overflow-hidden"
      data-testid="ace-response"
    >
      <CardContent className="p-0">
        {/* Direct Answer */}
        <div className="p-5 border-b border-[#E2E8F0]" data-testid="direct-answer">
          <p className="text-[#0F172A] leading-relaxed">{direct_answer}</p>
        </div>

        {/* Next Steps */}
        {next_steps.length > 0 && (
          <div className="p-5 border-b border-[#E2E8F0] bg-[#F8FAFC]" data-testid="next-steps">
            <p className="text-xs font-semibold text-[#475569] uppercase tracking-wider mb-3">
              Next Steps
            </p>
            <ol className="space-y-2">
              {next_steps.map((step, index) => (
                <li key={index} className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-5 h-5 rounded-full bg-[#001E44] text-white text-xs flex items-center justify-center font-medium">
                    {index + 1}
                  </span>
                  <span className="text-sm text-[#0F172A] leading-relaxed pt-0.5">{step}</span>
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Sources - Collapsible */}
        {sources_used.length > 0 && (
          <Collapsible open={sourcesOpen} onOpenChange={setSourcesOpen}>
            <CollapsibleTrigger asChild>
              <button 
                className="w-full p-4 flex items-center justify-between text-left hover:bg-[#F8FAFC] transition-colors border-b border-[#E2E8F0]"
                data-testid="sources-trigger"
              >
                <span className="text-xs font-medium text-[#475569]">
                  View sources ({sources_used.length})
                </span>
                <ChevronDown 
                  className={`w-4 h-4 text-[#475569] transition-transform duration-200 ${
                    sourcesOpen ? 'rotate-180' : ''
                  }`} 
                />
              </button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="p-4 bg-[#F8FAFC] space-y-2" data-testid="sources-list">
                {sources_used.map((source, index) => (
                  <a
                    key={index}
                    href={source.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center justify-between p-3 bg-white rounded-lg border border-[#E2E8F0] hover:border-[#96BEE6] transition-colors group"
                    data-testid={`source-${source.vault_id}`}
                  >
                    <div className="min-w-0">
                      <p className="text-xs font-mono text-[#94A3B8] mb-0.5">
                        {source.vault_id}
                      </p>
                      <p className="text-sm text-[#0F172A] truncate">
                        {source.title}
                      </p>
                    </div>
                    <ExternalLink className="w-4 h-4 text-[#94A3B8] group-hover:text-[#001E44] flex-shrink-0 ml-3" />
                  </a>
                ))}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* Risk Indicator & Advisor Button */}
        <div className="p-4 flex items-center justify-between bg-white">
          <Badge 
            variant="outline" 
            className={`${riskConfig.color} gap-1.5 py-1 px-2.5`}
            data-testid="risk-indicator"
          >
            {riskConfig.icon}
            {riskConfig.label}
          </Badge>

          {advisor_needed && (
            <Button
              variant="outline"
              size="sm"
              className="text-[#001E44] border-[#001E44] hover:bg-[#001E44] hover:text-white gap-2"
              data-testid="schedule-advisor-button"
            >
              <Calendar className="w-4 h-4" />
              Schedule advising
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
};

export default ACEResponse;
