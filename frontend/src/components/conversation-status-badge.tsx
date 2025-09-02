// src/components/conversation-status-badge.tsx

import { Badge } from "@/components/ui/badge";
import { 
  Circle, 
  CheckCircle, 
  XCircle,
  RefreshCw,
  AlertCircle,
  TrendingUp,
  TrendingDown,
  Mail
} from "lucide-react";

interface ConversationStatusBadgeProps {
  status: string;
  isCompleted?: boolean;
}

export function ConversationStatusBadge({ status, isCompleted }: ConversationStatusBadgeProps) {
  const getStatusConfig = () => {
    if (isCompleted) {
      switch (status) {
        case 'success':
          return {
            variant: "success",
            icon: CheckCircle,
            label: "Succès"
          };
        case 'failed':
          return {
            variant: "destructive",
            icon: XCircle,
            label: "Échec"
          };
        case 'resiliation':
          return {
            variant: "destructive",
            icon: TrendingDown,
            label: "Résiliation"
          };
        default:
          return {
            variant: "outline",
            icon: AlertCircle,
            label: status.replace('_', ' ')
          };
      }
    } else {
      switch (status) {
        case 'active':
        case 'nouvelle_opportunite':
        case 'upsell_cross_sell':
          return {
            variant: "default",
            icon: Circle,
            label: "Active"
          };
        case 'resiliation':
          return {
            variant: "destructive",
            icon: TrendingDown,
            label: "Résiliation"
          };
        case 'reclamation':
        case 'support_information':
          return {
            variant: "outline",
            icon: Mail,
            label: "Support"
          };
        default:
          return {
            variant: "outline",
            icon: AlertCircle,
            label: status.replace('_', ' ')
          };
      }
    }
  };

  const { variant, icon: Icon, label } = getStatusConfig();

  return (
    <Badge variant={variant as any} className="flex items-center gap-1">
      <Icon className="h-3 w-3" />
      {label}
    </Badge>
  );
}

interface MessageStatusBadgeProps {
  status: string;
}

export function MessageStatusBadge({ status }: MessageStatusBadgeProps) {
  const getStatusConfig = () => {
    switch (status) {
      case 'open':
        return {
          variant: "default",
          icon: Circle,
          label: "Nouveau"
        };
      case 'pending':
        return {
          variant: "outline",
          icon: AlertCircle,
          label: "En attente"
        };
      case 'validated':
        return {
          variant: "success",
          icon: CheckCircle,
          label: "Validé"
        };
      case 'sent':
        return {
          variant: "success",
          icon: CheckCircle,
          label: "Envoyé"
        };
      case 'blocked':
        return {
          variant: "destructive",
          icon: XCircle,
          label: "Bloqué"
        };
      default:
        return {
          variant: "outline",
          icon: AlertCircle,
          label: status
        };
    }
  };

  const { variant, icon: Icon, label } = getStatusConfig();

  return (
    <Badge variant={variant as any} className="flex items-center gap-1">
      <Icon className="h-3 w-3" />
      {label}
    </Badge>
  );
}