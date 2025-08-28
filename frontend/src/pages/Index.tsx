import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { HistoryIcon, CheckCircle2, Shield, Users, Loader2 } from "lucide-react"
import bhLogo from "@/assets/bh-logo.png"
import { useState, useEffect } from "react"

interface Stats {
  totalConversations: number
  pendingValidation: number
  satisfactionRate: number
  activeClients: number
  recentActivity?: string
}

const Index = () => {
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Charger les statistiques depuis l'API
  useEffect(() => {
    const fetchStats = async () => {
      try {
        setLoading(true)
        const response = await fetch('http://localhost:5000/api/stats')
        
        if (!response.ok) {
          throw new Error(`Erreur HTTP: ${response.status}`)
        }
        
        const data: Stats = await response.json()
        setStats(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erreur de chargement des statistiques')
        console.error('Erreur fetch stats:', err)
        
        // Fallback vers les données statiques en cas d'erreur
        setStats({
          totalConversations: 156,
          pendingValidation: 23,
          satisfactionRate: 98,
          activeClients: 45
        })
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
          {error && (
            <div className="bg-yellow-100 border border-yellow-400 text-yellow-800 px-4 py-3 rounded-md mb-6 max-w-2xl mx-auto">
              <p className="text-sm">⚠️ {error}</p>
              <p className="text-xs mt-1">Affichage des données de démonstration</p>
            </div>
          )}
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-2xl mx-auto">
            <Card>
              <CardContent className="pt-6">
                {loading ? (
                  <div className="flex flex-col items-center justify-center h-20">
                    <Loader2 className="h-6 w-6 animate-spin text-bh-navy mb-2" />
                    <p className="text-xs text-muted-foreground">Chargement...</p>
                  </div>
                ) : (
                  <>
                    <div className="text-3xl font-bold text-bh-navy mb-2">
                      {stats?.totalConversations || 0}
                    </div>
                    <p className="text-sm text-muted-foreground">Conversations totales</p>
                  </>
                )}
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="pt-6">
                {loading ? (
                  <div className="flex flex-col items-center justify-center h-20">
                    <Loader2 className="h-6 w-6 animate-spin text-bh-red mb-2" />
                    <p className="text-xs text-muted-foreground">Chargement...</p>
                  </div>
                ) : (
                  <>
                    <div className="text-3xl font-bold text-bh-red mb-2">
                      {stats?.pendingValidation || 0}
                    </div>
                    <p className="text-sm text-muted-foreground">En attente de validation</p>
                  </>
                )}
              </CardContent>
            </Card>
            
            <Card>
              <CardContent className="pt-6">
                {loading ? (
                  <div className="flex flex-col items-center justify-center h-20">
                    <Loader2 className="h-6 w-6 animate-spin text-green-600 mb-2" />
                    <p className="text-xs text-muted-foreground">Chargement...</p>
                  </div>
                ) : (
                  <>
                    <div className="text-3xl font-bold text-green-600 mb-2">
                      {stats?.satisfactionRate || 0}%
                    </div>
                    <p className="text-sm text-muted-foreground">Taux de satisfaction</p>
                  </>
                )}
              </CardContent>
            </Card>
          </div>
          
          {/* Dernière activité */}
          {stats?.recentActivity && (
            <div className="mt-6 text-center">
              <p className="text-sm text-muted-foreground">
                Dernière activité: {new Date(stats.recentActivity).toLocaleString('fr-FR')}
              </p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default Index;