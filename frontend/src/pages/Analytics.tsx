// src/app/analytics/page.tsx (ou src/components/Analytics.tsx)

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { 
  BarChart3, 
  MessageSquare, 
  CheckCircle, 
  Edit, 
  TrendingUp, 
  TrendingDown, 
  Users, 
  UserCheck, 
  UserMinus, 
  AlertTriangle 
} from "lucide-react"
import { useEffect, useState } from "react"

// Types
interface PerformanceStats {
  totalConversations: number
  messagesModifies: number
  nouvellesOpportunites: number
  renouvellements: number
  upsellCrossSell: number
  resiliations: number
  perteClients: number
  obtentionClients: number
  supportInformation: number
  reclamations: number
  prospectsFroids: number
}

interface MonthlyTrends {
  conversationsEvolution: number
  opportunitesEvolution: number
  resiliationsEvolution: number
  obtentionEvolution: number
}

interface AnalyticsResponse {
  data: PerformanceStats
  trends: MonthlyTrends
}

export default function Analytics() {
  const [data, setData] = useState<PerformanceStats | null>(null)
  const [trends, setTrends] = useState<MonthlyTrends | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const token = localStorage.getItem('token')
        if (!token) {
          throw new Error('Token manquant')
        }

        const res = await fetch('http://localhost:3001/api/analytics/summary?from=2025-01-01&to=2025-12-31', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })

        if (!res.ok) {
          throw new Error('Échec du chargement des données')
        }

        const result: AnalyticsResponse = await res.json()
        setData(result.data)
        setTrends(result.trends)
      } catch (err: any) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchAnalytics()
  }, [])

  if (loading) return <div className="p-6">Chargement des statistiques...</div>
  if (error) return <div className="p-6 text-red-500">Erreur: {error}</div>
  if (!data) return <div className="p-6">Aucune donnée disponible</div>

  const tauxConversion = ((data.obtentionClients / data.totalConversations) * 100).toFixed(1)
  const tauxResiliation = ((data.resiliations / data.totalConversations) * 100).toFixed(1)
  const tauxModification = ((data.messagesModifies / data.totalConversations) * 100).toFixed(1)

  const StatCard = ({ 
    title, 
    value, 
    icon: Icon, 
    trend, 
    className = "",
    description 
  }: {
    title: string
    value: string | number
    icon: any
    trend?: number
    className?: string
    description?: string
  }) => (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {description && (
          <p className="text-xs text-muted-foreground mt-1">{description}</p>
        )}
        {trend !== undefined && (
          <div className="flex items-center text-xs text-muted-foreground mt-2">
            {trend > 0 ? (
              <TrendingUp className="h-3 w-3 text-success mr-1" />
            ) : (
              <TrendingDown className="h-3 w-3 text-destructive mr-1" />
            )}
            {trend > 0 ? '+' : ''}{trend}% ce mois
          </div>
        )}
      </CardContent>
    </Card>
  )

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-primary">Analyse de Performance de l'Agent IA</h1>
        <p className="text-muted-foreground mt-2">
          Tableau de bord complet des performances et statistiques de l'agent IA BH Assurance
        </p>
      </div>

      {/* Vue d'ensemble */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-6">
        <StatCard
          title="Total Conversations"
          value={data.totalConversations}
          icon={MessageSquare}
          trend={trends?.conversationsEvolution}
          className="border-l-4 border-l-primary"
        />
        <StatCard
          title="Messages Modifiés"
          value={data.messagesModifies}
          icon={Edit}
          description={`${tauxModification}% du total`}
          className="border-l-4 border-l-accent"
        />
        <StatCard
          title="Taux de Conversion"
          value={`${tauxConversion}%`}
          icon={UserCheck}
          trend={trends?.obtentionEvolution}
          className="border-l-4 border-l-success"
        />
        <StatCard
          title="Taux de Résiliation"
          value={`${tauxResiliation}%`}
          icon={UserMinus}
          trend={trends?.resiliationsEvolution}
          className="border-l-4 border-l-destructive"
        />
      </div>

      {/* Opportunités et Résultats */}
      <div className="grid gap-6 md:grid-cols-2 mb-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-success" />
              Opportunités et Croissance
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Nouvelles Opportunités</span>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-success border-success">
                  {data.nouvellesOpportunites}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {((data.nouvellesOpportunites / data.totalConversations) * 100).toFixed(1)}%
                </span>
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Renouvellements</span>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-primary border-primary">
                  {data.renouvellements}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {((data.renouvellements / data.totalConversations) * 100).toFixed(1)}%
                </span>
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Upsell / Cross-sell</span>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-accent border-accent">
                  {data.upsellCrossSell}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {((data.upsellCrossSell / data.totalConversations) * 100).toFixed(1)}%
                </span>
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Obtention Clients</span>
              <div className="flex items-center gap-2">
                <Badge className="bg-success text-success-foreground">
                  {data.obtentionClients}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {tauxConversion}%
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              Résiliations et Défis
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Résiliations</span>
              <div className="flex items-center gap-2">
                <Badge variant="destructive">
                  {data.resiliations}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {tauxResiliation}%
                </span>
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Perte Clients</span>
              <div className="flex items-center gap-2">
                <Badge variant="destructive">
                  {data.perteClients}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {((data.perteClients / data.totalConversations) * 100).toFixed(1)}%
                </span>
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Prospects Froids</span>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-muted-foreground border-muted-foreground">
                  {data.prospectsFroids}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {((data.prospectsFroids / data.totalConversations) * 100).toFixed(1)}%
                </span>
              </div>
            </div>
            
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Réclamations</span>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-orange-600 border-orange-600">
                  {data.reclamations}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {((data.reclamations / data.totalConversations) * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Support et Information */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5 text-primary" />
            Support et Information
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">Support / Information</span>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-blue-600 border-blue-600">
                  {data.supportInformation}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {((data.supportInformation / data.totalConversations) * 100).toFixed(1)}%
                </span>
              </div>
            </div>
            
            <div className="text-xs text-muted-foreground">
              Demandes d'information sans intention d'achat direct
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Résumé de Performance */}
      <Card className="mt-6 border-l-4 border-l-primary">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-primary" />
            Résumé de Performance
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="text-center">
              <div className="text-2xl font-bold text-success">{tauxConversion}%</div>
              <div className="text-sm text-muted-foreground">Taux de Conversion</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-accent">{tauxModification}%</div>
              <div className="text-sm text-muted-foreground">Messages Modifiés</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-primary">
                {((data.nouvellesOpportunites + data.renouvellements + data.upsellCrossSell) / data.totalConversations * 100).toFixed(1)}%
              </div>
              <div className="text-sm text-muted-foreground">Opportunités Totales</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}