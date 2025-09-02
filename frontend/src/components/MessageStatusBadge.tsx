import { Badge } from "@/components/ui/badge";
import { 
  Circle, 
  Clock, 
  CheckCircle, 
  XCircle,
  RefreshCw
} from "lucide-react";

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
          icon: Clock,
          label: "En attente validation"
        };
      case 'validated':
        return {
          variant: "outline",
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
          icon: RefreshCw,
          label: status
        };
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