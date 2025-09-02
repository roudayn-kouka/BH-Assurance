// src/app/historique/page.tsx

import { useState, useEffect } from "react"
import { ArrowLeft, MessageCircle, User } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { EmailMessage, generateSubject } from "@/components/EmailMessage"

// Types
interface Client {
  id: string
  nom: string
  email: string
  telephone: string
  dernierContact: string
  nombreMessages: number
  conversationTerminee: boolean
}

interface Message {
  id: string
  contenu: string
  expediteur: "client" | "agent" | "ai"
  timestamp: string
  type?: "question" | "reponse"
  body: string
  sender: string
  created_at: string
  direction: "inbox" | "sent"
}

export default function Historique() {
  const [clients, setClients] = useState<Client[]>([])
  const [conversations, setConversations] = useState<Record<string, Message[]>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedClient, setSelectedClient] = useState<Client | null>(null)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const token = localStorage.getItem('token')
        if (!token) throw new Error('Non authentifié')

        const headers = { 'Authorization': `Bearer ${token}` }

        // 🔹 Charger les clients
        const clientsRes = await fetch('http://localhost:3001/api/clients', { headers })
        if (!clientsRes.ok) throw new Error('Échec du chargement des clients')

        const clientsData = await clientsRes.json()

        // ✅ Gestion de la réponse paginée : extraire `clients` si présent
        const clientsArray = Array.isArray(clientsData)
          ? clientsData
          : Array.isArray(clientsData.clients)
            ? clientsData.clients
            : []

        const formattedClients: Client[] = clientsArray.map((c: any) => ({
          id: c._id,
          nom: `${c.first_name} ${c.last_name}`.trim() || 'Client inconnu',
          email: c.email,
          telephone: c.phone || 'Non renseigné',
          dernierContact: new Date(c.last_contact_at).toLocaleString('fr-TN'),
          nombreMessages: 0,
          conversationTerminee: false
        }))
        setClients(formattedClients)

        // 🔹 Charger les conversations et messages
        const conversationsData: Record<string, Message[]> = {}
        for (const client of formattedClients) {
          const convRes = await fetch(`http://localhost:3001/api/conversations?client_id=${client.id}`, { headers })
          const convsData = await convRes.json()

          // ✅ Extraire le tableau de conversations
          const convs = Array.isArray(convsData)
            ? convsData
            : Array.isArray(convsData.conversations)
              ? convsData.conversations
              : []

          let messages: Message[] = []
          for (const conv of convs) {
            const msgRes = await fetch(`http://localhost:3001/api/conversations/${conv._id}/messages`, { headers })
            const msgsData = await msgRes.json()

            // ✅ Extraire les messages
            const msgs = Array.isArray(msgsData)
              ? msgsData
              : Array.isArray(msgsData.messages)
                ? msgsData.messages
                : []

            messages = messages.concat(
              msgs.map((m: any) => ({
                id: m._id,
                contenu: m.body,
                expediteur: m.sender === 'client' ? 'client' : 'agent',
                timestamp: new Date(m.created_at).toLocaleString('fr-TN'),
                body: m.body,
                sender: m.sender,
                created_at: m.created_at,
                direction: m.direction,
                type: m.sender === 'client' ? 'question' : 'reponse'
              }))
            )

            // Mettre à jour statut
            client.nombreMessages = messages.length
            client.conversationTerminee = conv.is_completed
          }

          conversationsData[client.id] = messages.sort((a, b) => 
            new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          )
        }

        setConversations(conversationsData)
      } catch (err: any) {
        console.error('Erreur dans Historique:', err)
        setError(err.message || 'Une erreur inattendue est survenue')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  if (loading) return <div className="p-6">Chargement de l'historique...</div>
  if (error) return <div className="p-6 text-red-500">Erreur: {error}</div>

  // ✅ Si aucun client n'existe
  if (!loading && clients.length === 0) {
    return (
      <div className="p-6">
        <h1 className="text-3xl font-bold text-primary mb-6">Historique des conversations</h1>
        <Card className="text-center py-10">
          <CardContent>
            <User className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-xl font-semibold mb-2">Aucun client trouvé</h3>
            <p className="text-muted-foreground mb-4">
              Aucun client n’a encore été créé dans le système.
            </p>
            <p className="text-sm text-muted-foreground">
              Les conversations apparaîtront ici dès qu’un client interagira avec l’agent IA.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (selectedClient) {
    const messages = conversations[selectedClient.id] || []
    
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
                <p className="text-sm text-muted-foreground">Dernier contact</p>
                <p className="font-medium">{selectedClient.dernierContact}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageCircle className="h-5 w-5" />
              Historique des échanges ({messages.length} messages)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {messages.map((message) => {
                const isClient = message.expediteur === "client"
                return (
                  <EmailMessage
                    key={message.id}
                    from={isClient ? selectedClient.nom : "Agent IA BH Assurance"}
                    fromEmail={isClient ? selectedClient.email : "support@bh-assurance.tn"}
                    to={isClient ? "Agent IA BH Assurance" : selectedClient.nom}
                    toEmail={isClient ? "support@bh-assurance.tn" : selectedClient.email}
                    subject={generateSubject(message.type, message.contenu)}
                    date={message.timestamp}
                    body={message.contenu}
                    direction={isClient ? "inbox" : "sent"}
                    tag={message.type === "question" ? "Question" : "Réponse"}
                  />
                )
              })}
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-primary mb-6">Historique des conversations</h1>
      
      <div className="grid gap-4">
        {clients.map((client) => (
          <Card 
            key={client.id} 
            className="cursor-pointer hover:shadow-lg transition-shadow border-l-4 border-l-bh-red"
            onClick={() => setSelectedClient(client)}
          >
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-3">
                  <User className="h-5 w-5 text-bh-navy" />
                  {client.nom}
                </CardTitle>
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-bh-navy border-bh-navy">
                    {client.nombreMessages} messages
                  </Badge>
                  <Badge variant={client.conversationTerminee ? "default" : "destructive"}>
                    {client.conversationTerminee ? "Terminée" : "En cours"}
                  </Badge>
                </div>
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
                  <p className="text-muted-foreground">Dernier contact</p>
                  <p className="font-medium">{client.dernierContact}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}