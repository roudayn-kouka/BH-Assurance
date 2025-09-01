import { Mail, Calendar, User } from "lucide-react"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

interface EmailMessageProps {
  from: string
  fromEmail: string
  to: string
  toEmail: string
  subject: string
  date: string
  body: string
  direction: "inbox" | "sent"
  tag?: string
}

const generateSubject = (type: "question" | "reponse" | undefined, content: string): string => {
  if (type === "question") {
    // Extract first part of the question for subject
    const firstSentence = content.split('.')[0] || content.substring(0, 50)
    return `Question: ${firstSentence}${firstSentence.length < content.length ? '...' : ''}`
  } else if (type === "reponse") {
    return "Réponse de BH Assurance à votre demande"
  }
  return "Échange avec BH Assurance"
}

export function EmailMessage({ 
  from, 
  fromEmail, 
  to, 
  toEmail, 
  subject, 
  date, 
  body, 
  direction,
  tag 
}: EmailMessageProps) {
  return (
    <Card className={`transition-all hover:shadow-md ${
      direction === "inbox" 
        ? "border-l-4 border-l-bh-navy bg-card" 
        : "border-l-4 border-l-bh-red bg-primary/5"
    }`}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <Mail className={`h-4 w-4 ${direction === "inbox" ? "text-bh-navy" : "text-bh-red"}`} />
            <span className="font-semibold text-sm">{subject}</span>
          </div>
          {tag && (
            <Badge 
              variant={direction === "inbox" ? "secondary" : "default"}
              className={direction === "inbox" ? "bg-bh-navy/10 text-bh-navy border-bh-navy/20" : "bg-bh-red/10 text-bh-red border-bh-red/20"}
            >
              {tag}
            </Badge>
          )}
        </div>
        
        <div className="space-y-1 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <User className="h-3 w-3" />
            <span><strong>De:</strong> {from} &lt;{fromEmail}&gt;</span>
          </div>
          <div className="flex items-center gap-2">
            <User className="h-3 w-3" />
            <span><strong>À:</strong> {to} &lt;{toEmail}&gt;</span>
          </div>
          <div className="flex items-center gap-2">
            <Calendar className="h-3 w-3" />
            <span><strong>Date:</strong> {new Date(date).toLocaleString('fr-FR')}</span>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="pt-0">
        <div className="bg-background/50 p-4 rounded-md border border-border/50">
          <p className="text-sm leading-relaxed whitespace-pre-line">
            {body}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

export { generateSubject }