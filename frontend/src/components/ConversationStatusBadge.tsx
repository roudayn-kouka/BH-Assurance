import { Badge } from "@/components/ui/badge";
import { 
  Circle, 
  Clock, 
  CheckCircle, 
  XCircle,
  RefreshCw,
  AlertCircle
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
        case 'resiliation':
          return {
            variant: "destructive",
            icon: XCircle,
            label: "Résiliation"
          };
        case 'new_opportunity':
          return {
            variant: "outline",
            icon: RefreshCw,
            label: "Nouvelle opportunité"
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
          return {
            variant: "default",
            icon: Circle,
            label: "Active"
          };
        case 'blocked':
          return {
            variant: "outline",
            icon: Clock,
            label: "En attente réponse"
          };
        default:
          return {
            variant: "outline",
            icon: AlertCircle,
            label: status
          };
      }
    }
  };

  const { variant, icon: Icon, label } = getStatusConfig();

  return (
    <Badge variant={variant as any}>
      <Icon className="h-3 w-3 mr-1" />
      {label}
    </Badge>
  );
}