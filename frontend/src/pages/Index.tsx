// src/app/page.tsx (ou src/components/Index.tsx)

import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { HistoryIcon, CheckCircle2, Shield, Users } from "lucide-react"
import bhLogo from "@/assets/bh-logo.png"

interface AnalyticsSummary {
  totalConversations: number
  pendingValidations: number
  satisfactionRate: number
}

const Index = () => {
  const [stats, setStats] = useState<AnalyticsSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const token = localStorage.getItem('token')
        if (!token) throw new Error('Non authentifié')

        const res = await fetch('http://localhost:3001/api/analytics/summary', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })

        if (!res.ok) {
          throw new Error('Échec du chargement des statistiques')
        }

        const data = await res.json()

        // Adapter les données API → frontend
        setStats({
          totalConversations: data.total_conversations || 0,
          pendingValidations: data.pending_validations || 0,
          satisfactionRate: data.satisfaction_rate ? Math.round(data.satisfaction_rate * 100) : 98 // Valeur par défaut
        })
      } catch (err: any) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-bh-light-blue">
      {/* Header */}
      <header className="border-b bg-card/80 backdrop-blur-sm">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <img src={bhLogo} alt="BH Assurance" className="h-12" />
              <div>
                <h1 className="text-2xl font-bold text-primary">Dashboard Administrateur</h1>
                <p className="text-muted-foreground">Gestion de l'Agent IA</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-bh-navy" />
              <span className="text-sm text-muted-foreground">Admin</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-6 py-12">
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold text-primary mb-4">
            Bienvenue sur votre dashboard
          </h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Gérez efficacement les conversations de votre agent IA et validez les réponses pour offrir un service client optimal.
          </p>
        </div>

        {/* Feature Cards */}
        <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          <Card className="border-l-4 border-l-bh-navy hover:shadow-lg transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-3 text-bh-navy">
                <HistoryIcon className="h-6 w-6" />
                Historique des conversations
              </CardTitle>
              <CardDescription>
                Consultez et analysez toutes les conversations entre l'agent IA et vos clients
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-muted-foreground mb-6">
                <li className="flex items-center gap-2">
                  <Users className="h-4 w-4" />
                  Liste complète des clients
                </li>
                <li className="flex items-center gap-2">
                  <Users className="h-4 w-4" />
                  Détail des échanges par client
                </li>
                <li className="flex items-center gap-2">
                  <Users className="h-4 w-4" />
                  Historique complet des interactions
                </li>
              </ul>
              <Link to="/historique">
                <Button className="w-full bg-bh-navy hover:bg-bh-navy/90">
                  Accéder à l'historique
                </Button>
              </Link>
            </CardContent>
          </Card>

          <Card className="border-l-4 border-l-bh-red hover:shadow-lg transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center gap-3 text-bh-red">
                <CheckCircle2 className="h-6 w-6" />
                Validation des réponses
              </CardTitle>
              <CardDescription>
                Validez, modifiez ou consultez les réponses de l'agent IA avant envoi
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-muted-foreground mb-6">
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  Réponses en attente de validation
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  Modification et argumentation
                </li>
                <li className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  Envoi automatique par email
                </li>
              </ul>
              <Link to="/validation">
                <Button className="w-full bg-bh-red hover:bg-bh-red/90">
                  Gérer les validations
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>

        {/* Stats Section */}
        <div className="mt-16 text-center">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-2xl mx-auto">
            <Card>
              <CardContent className="pt-6">
                {loading ? (
                  <div className="text-3xl font-bold text-muted-foreground">...</div>
                ) : error ? (
                  <div className="text-sm text-destructive">Erreur</div>
                ) : (
                  <>
                    <div className="text-3xl font-bold text-bh-navy mb-2">{stats?.totalConversations}</div>
                    <p className="text-sm text-muted-foreground">Conversations totales</p>
                  </>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                {loading ? (
                  <div className="text-3xl font-bold text-muted-foreground">...</div>
                ) : error ? (
                  <div className="text-sm text-destructive">Erreur</div>
                ) : (
                  <>
                    <div className="text-3xl font-bold text-bh-red mb-2">{stats?.pendingValidations}</div>
                    <p className="text-sm text-muted-foreground">En attente de validation</p>
                  </>
                )}
              </CardContent>
            </Card>
            <Card>
              <CardContent className="pt-6">
                {loading ? (
                  <div className="text-3xl font-bold text-muted-foreground">...</div>
                ) : error ? (
                  <div className="text-sm text-destructive">Erreur</div>
                ) : (
                  <>
                    <div className="text-3xl font-bold text-success mb-2">{stats?.satisfactionRate}%</div>
                    <p className="text-sm text-muted-foreground">Taux de satisfaction</p>
                  </>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  )
}

export default Index