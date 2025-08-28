import { useState, useEffect } from "react"
import { ArrowLeft, MessageCircle, User, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { EmailMessage, generateSubject } from "@/components/EmailMessage"

interface Client {
  _id: string
  nom: string
  email: string
  telephone: string
  statut: string
  dateCreation?: string
}

interface Conversation {
  _id: string
  clientId: string
  sujet: string
  statut: string
  dernierContact: string
  nombreMessages: number
  satisfaction: number
}

interface Message {
  _id: string
  conversationId: string
  expediteur: "client" | "agent"
  type: string
  sujet: string
  corps: string
  statut: string
  dateEnvoi?: string
  createdAt: string
}

interface ApiResponse<T> {
  clients?: T[]
  conversations?: T[]
  messages?: T[]
  currentPage?: number
  totalPages?: number
  totalClients?: number
  totalConversations?: number
  totalMessages?: number
}

export default function Historique() {
  const [selectedClient, setSelectedClient] = useState<Client | null>(null)
  const [clients, setClients] = useState<Client[]>([])
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Charger les clients depuis l'API
  useEffect(() => {
    const fetchClients = async () => {
      try {
        setLoading(true)
        const response = await fetch('http://localhost:5000/api/clients')
        
        if (!response.ok) {
          throw new Error(`Erreur HTTP: ${response.status}`)
        }
        
        const data: Client[] = await response.json()
        setClients(data)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erreur de chargement')
        console.error('Erreur fetch clients:', err)
        
        // Fallback vers les données mockées en cas d'erreur
        setClients([
          {
            _id: "1",
            nom: "Sarra Mabrouk",
            email: "sarra.mabrouk@gmail.com",
            telephone: "+216 22 345 678",
            statut: "actif"
          },
          {
            _id: "2", 
            nom: "Karim Sassi",
            email: "karim.sassi@gmail.com",
            telephone: "+216 98 123 456",
            statut: "actif"
          },
          {
            _id: "3",
            nom: "Ahmed Ben Ali",
            email: "ahmed.benali@email.com",
            telephone: "+216 20 123 456",
            statut: "actif"
          }
        ])
      } finally {
        setLoading(false)
      }
    }

    fetchClients()
  }, [])

  // Charger les conversations d'un client sélectionné
  useEffect(() => {
    const fetchConversations = async () => {
      if (!selectedClient) return

      try {
        setLoading(true)
        // Note: Votre backend actuel n'a pas d'endpoint spécifique pour les conversations par client
        // On utilise donc toutes les conversations et on filtre côté client
        const response = await fetch('http://localhost:5000/api/conversations')
        
        if (!response.ok) {
          throw new Error(`Erreur HTTP: ${response.status}`)
        }
        
        const data: Conversation[] = await response.json()
        // Filtrer les conversations pour ce client
        const clientConversations = data.filter(conv => conv.clientId === selectedClient._id)
        setConversations(clientConversations)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erreur de chargement des conversations')
        console.error('Erreur fetch conversations:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchConversations()
  }, [selectedClient])

  // Charger les messages d'une conversation
  const fetchMessages = async (clientId: string) => {
    try {
      setLoading(true)
      const response = await fetch('http://localhost:5000/api/messages/pending')
      
      if (!response.ok) {
        throw new Error(`Erreur HTTP: ${response.status}`)
      }
      
      const data: Message[] = await response.json()
      // Filtrer les messages pour ce client (simulation)
      const clientMessages = data.filter(msg => 
        msg.conversationId === '1' // Adaptation temporaire
      )
      setMessages(clientMessages)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur de chargement des messages')
      console.error('Erreur fetch messages:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading && clients.length === 0) {
    return (
      <div className="p-6 flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-bh-red" />
          <p className="mt-2 text-muted-foreground">Chargement des clients...</p>
        </div>
      </div>
    )
  }

  if (error && clients.length === 0) {
    return (
      <div className="p-6">
        <div className="bg-destructive/15 text-destructive p-4 rounded-md">
          <p>Erreur: {error}</p>
          <p className="text-sm mt-2">Utilisation des données de démonstration</p>
        </div>
      </div>
    )
  }

  if (selectedClient) {
    return (
      <div className="p-6">
        <div className="flex items-center gap-4 mb-6">
          <Button 
            variant="outline" 
            onClick={() => setSelectedClient(null)}
            className="flex items-center gap-2"
          >
            <ArrowLeft className="h-4 w-4" />
            Retour à la liste
          </Button>
          <h1 className="text-2xl font-bold text-primary">
            Conversation avec {selectedClient.nom}
          </h1>
        </div>

        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Informations du client
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-3 gap-4">
              <div>
                <p className="text-sm text-muted-foreground">Email</p>
                <p className="font-medium">{selectedClient.email}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Téléphone</p>
                <p className="font-medium">{selectedClient.telephone}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Statut</p>
                <Badge 
                  variant={selectedClient.statut === 'actif' ? 'default' : 'secondary'}
                  className={selectedClient.statut === 'actif' ? 'bg-green-100 text-green-800' : ''}
                >
                  {selectedClient.statut}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageCircle className="h-5 w-5" />
              Historique des échanges
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="text-center py-8">
                <Loader2 className="h-6 w-6 animate-spin mx-auto text-bh-red" />
                <p className="mt-2 text-muted-foreground">Chargement des messages...</p>
              </div>
            ) : messages.length > 0 ? (
              <div className="space-y-4">
                {messages.map((message) => {
                  const isClient = message.expediteur === "client"
                  return (
                    <EmailMessage
                      key={message._id}
                      from={isClient ? selectedClient.nom : "Agent IA BH Assurance"}
                      fromEmail={isClient ? selectedClient.email : "support@bh-assurance.tn"}
                      to={isClient ? "Agent IA BH Assurance" : selectedClient.nom}
                      toEmail={isClient ? "support@bh-assurance.tn" : selectedClient.email}
                      subject={message.sujet || generateSubject('question', message.corps)}
                      date={message.createdAt}
                      body={message.corps}
                      direction={isClient ? "inbox" : "sent"}
                      tag={isClient ? "Question" : "Réponse"}
                      status={message.statut}
                    />
                  )
                })}
              </div>
            ) : (
              <div className="text-center py-8 text-muted-foreground">
                <MessageCircle className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>Aucun message trouvé pour ce client</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-primary mb-6">Historique des conversations</h1>
      
      {error && (
        <div className="bg-destructive/15 text-destructive p-4 rounded-md mb-4">
          <p>Attention: {error}</p>
          <p className="text-sm mt-2">Affichage des données de démonstration</p>
        </div>
      )}
      
      <div className="grid gap-4">
        {clients.map((client) => (
          <Card 
            key={client._id} 
            className="cursor-pointer hover:shadow-lg transition-shadow border-l-4 border-l-bh-red"
            onClick={() => {
              setSelectedClient(client)
              fetchMessages(client._id)
            }}
          >
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-3">
                  <User className="h-5 w-5 text-bh-navy" />
                  {client.nom}
                </CardTitle>
                <Badge variant="outline" className="text-bh-navy border-bh-navy">
                  Client {client.statut}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Email</p>
                  <p className="font-medium">{client.email}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Téléphone</p>
                  <p className="font-medium">{client.telephone}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Statut</p>
                  <Badge 
                    variant={client.statut === 'actif' ? 'default' : 'secondary'}
                    className={client.statut === 'actif' ? 'bg-green-100 text-green-800' : ''}
                  >
                    {client.statut}
                  </Badge>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}