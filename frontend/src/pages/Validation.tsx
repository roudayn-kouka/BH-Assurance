import { useState, useEffect } from "react"
import { ArrowLeft, CheckCircle, Edit, FileText, Mail, AlertCircle, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/hooks/use-toast"
import { EmailMessage, generateSubject } from "@/components/EmailMessage"

interface Client {
  _id: string
  nom: string
  email: string
  telephone: string
  statut: string
}

interface PendingMessage {
  _id: string
  conversationId: string
  expediteur: "client" | "agent"
  type: string
  sujet: string
  corps: string
  statut: string
  createdAt: string
  justification?: string
  client?: Client
}

export default function Validation() {
  const [clients, setClients] = useState<Client[]>([])
  const [pendingMessages, setPendingMessages] = useState<PendingMessage[]>([])
  const [selectedClient, setSelectedClient] = useState<Client | null>(null)
  const [editingMessage, setEditingMessage] = useState<PendingMessage | null>(null)
  const [editedContent, setEditedContent] = useState("")
  const [showArgumentation, setShowArgumentation] = useState<PendingMessage | null>(null)
  const [loading, setLoading] = useState(true)
  const { toast } = useToast()

  // Charger les messages en attente
  useEffect(() => {
    const fetchPendingMessages = async () => {
      try {
        setLoading(true)
        const response = await fetch('http://localhost:5000/api/messages/pending')
        
        if (!response.ok) {
          throw new Error(`Erreur HTTP: ${response.status}`)
        }
        
        const data: PendingMessage[] = await response.json()
        setPendingMessages(data)
        
        // Extraire les clients uniques des messages
        const uniqueClients = data.reduce((acc: Client[], message) => {
          if (message.client && !acc.find(c => c._id === message.client?._id)) {
            acc.push(message.client)
          }
          return acc
        }, [])
        
        setClients(uniqueClients)
        
      } catch (err) {
        console.error('Erreur fetch pending messages:', err)
        toast({
          title: "Erreur de chargement",
          description: "Impossible de charger les messages en attente",
          variant: "destructive",
        })
        
        // Fallback vers les données mockées
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
          }
        ])
        
        setPendingMessages([
          {
            _id: "1",
            conversationId: "1",
            expediteur: "agent",
            type: "email",
            sujet: "Réponse: Résiliation de contrat",
            corps: "Oui, vous pouvez résilier votre contrat à tout moment en respectant un préavis de 30 jours. Des frais de résiliation anticipée de 50 DT peuvent s'appliquer selon les conditions générales de votre contrat.",
            statut: "en_attente",
            createdAt: "2024-01-15T16:18:00.000Z",
            justification: "Selon l'article 12 des conditions générales BH Assurance, le client peut résilier son contrat moyennant un préavis de 30 jours. Les frais mentionnés correspondent au barème tarifaire en vigueur.",
            client: {
              _id: "1",
              nom: "Sarra Mabrouk",
              email: "sarra.mabrouk@gmail.com",
              telephone: "+216 22 345 678",
              statut: "actif"
            }
          }
        ])
      } finally {
        setLoading(false)
      }
    }

    fetchPendingMessages()
  }, [toast])

  const handleValider = async (messageId: string) => {
    try {
      const response = await fetch(`http://localhost:5000/api/messages/${messageId}/validate`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ justification: "Validé par administrateur" })
      })

      if (response.ok) {
        toast({
          title: "Réponse validée",
          description: "La réponse a été validée et envoyée au client",
          variant: "default",
        })

        // Mettre à jour la liste locale
        setPendingMessages(prev => prev.filter(msg => msg._id !== messageId))
        
        // Mettre à jour la liste des clients si nécessaire
        const updatedMessages = pendingMessages.filter(msg => msg._id !== messageId)
        const remainingClientIds = new Set(updatedMessages.map(msg => msg.client?._id))
        setClients(prev => prev.filter(client => remainingClientIds.has(client._id)))

      } else {
        throw new Error("Échec de la validation")
      }
    } catch (error) {
      toast({
        title: "Erreur de validation",
        description: "Impossible de valider la réponse",
        variant: "destructive",
      })
    }
  }

  const handleModifier = (message: PendingMessage) => {
    setEditingMessage(message)
    setEditedContent(message.corps)
  }

  const handleConfirmerModification = async () => {
    if (!editingMessage) return

    try {
      const response = await fetch(`http://localhost:5000/api/messages/${editingMessage._id}/update`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          corps: editedContent,
          justification: "Modifié par administrateur"
        })
      })

      if (response.ok) {
        toast({
          title: "Réponse modifiée",
          description: "La réponse modifiée a été envoyée au client",
          variant: "default",
        })

        // Mettre à jour la liste locale
        setPendingMessages(prev => prev.filter(msg => msg._id !== editingMessage._id))
        setEditingMessage(null)
        setEditedContent("")

      } else {
        throw new Error("Échec de la modification")
      }
    } catch (error) {
      toast({
        title: "Erreur de modification",
        description: "Impossible de modifier la réponse",
        variant: "destructive",
      })
    }
  }

  // Regrouper les messages par client
  const messagesByClient = pendingMessages.reduce((acc, message) => {
    const clientId = message.client?._id || 'unknown'
    if (!acc[clientId]) {
      acc[clientId] = []
    }
    acc[clientId].push(message)
    return acc
  }, {} as Record<string, PendingMessage[]>)

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center min-h-screen">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto text-bh-red" />
          <p className="mt-2 text-muted-foreground">Chargement des messages en attente...</p>
        </div>
      </div>
    )
  }

  if (selectedClient) {
    const clientMessages = messagesByClient[selectedClient._id] || []

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
            Validation - {selectedClient.nom}
          </h1>
          <Badge variant="destructive">
            {clientMessages.length} réponse(s) en attente
          </Badge>
        </div>

        <div className="space-y-6">
          {clientMessages.map((message) => (
            <Card key={message._id} className="border-l-4 border-l-accent">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-accent" />
                  Réponse en attente de validation
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  Reçue le {new Date(message.createdAt).toLocaleString('fr-FR')}
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-4">
                  <div>
                    <h4 className="font-medium text-bh-navy mb-2">Réponse de l'agent IA (en attente de validation) :</h4>
                    <EmailMessage
                      from="Agent IA BH Assurance"
                      fromEmail="support@bh-assurance.tn"
                      to={selectedClient.nom}
                      toEmail={selectedClient.email}
                      subject={message.sujet || "Réponse de BH Assurance"}
                      date={message.createdAt}
                      body={message.corps}
                      direction="sent"
                      tag="Réponse en attente"
                    />
                  </div>
                </div>

                <div className="flex gap-3 pt-4">
                  <Button 
                    onClick={() => handleValider(message._id)}
                    className="bg-success hover:bg-success/90"
                  >
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Valider
                  </Button>
                  
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button 
                        variant="outline"
                        onClick={() => handleModifier(message)}
                      >
                        <Edit className="h-4 w-4 mr-2" />
                        Modifier
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-2xl">
                      <DialogHeader>
                        <DialogTitle>Modifier la réponse</DialogTitle>
                        <DialogDescription>
                          Modifiez la réponse de l'agent IA avant de l'envoyer au client.
                        </DialogDescription>
                      </DialogHeader>
                      <Textarea
                        value={editedContent}
                        onChange={(e) => setEditedContent(e.target.value)}
                        className="min-h-[120px]"
                        placeholder="Modifiez la réponse..."
                      />
                      <DialogFooter>
                        <Button 
                          onClick={handleConfirmerModification}
                          className="bg-success hover:bg-success/90"
                        >
                          <Mail className="h-4 w-4 mr-2" />
                          Confirmer et envoyer
                        </Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>

                  {message.justification && (
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button 
                          variant="outline"
                          onClick={() => setShowArgumentation(message)}
                        >
                          <FileText className="h-4 w-4 mr-2" />
                          Argumentation
                        </Button>
                      </DialogTrigger>
                      <DialogContent>
                        <DialogHeader>
                          <DialogTitle>Argumentation de l'agent IA</DialogTitle>
                          <DialogDescription>
                            Justification de la réponse fournie par l'agent IA.
                          </DialogDescription>
                        </DialogHeader>
                        <div className="bg-muted p-4 rounded-lg">
                          <p className="text-sm leading-relaxed">
                            {message.justification}
                          </p>
                        </div>
                      </DialogContent>
                    </Dialog>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold text-primary mb-6">Validation des réponses</h1>
      <p className="text-muted-foreground mb-6">
        Clients avec des réponses en attente de validation, triés par priorité.
      </p>

      {Object.keys(messagesByClient).length === 0 ? (
        <div className="text-center py-12">
          <CheckCircle className="h-16 w-16 text-green-500 mx-auto mb-4" />
          <h2 className="text-2xl font-semibold text-muted-foreground mb-2">
            Aucun message en attente
          </h2>
          <p className="text-muted-foreground">
            Toutes les réponses ont été validées. Bravo !
          </p>
        </div>
      ) : (
        <div className="grid gap-4">
          {clients.map((client) => {
            const clientMessages = messagesByClient[client._id] || []
            return (
              <Card 
                key={client._id} 
                className="cursor-pointer hover:shadow-lg transition-shadow border-l-4 border-l-accent"
                onClick={() => setSelectedClient(client)}
              >
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="flex items-center gap-3">
                      <AlertCircle className="h-5 w-5 text-accent" />
                      {client.nom}
                    </CardTitle>
                    <Badge variant="destructive">
                      {clientMessages.length} réponse(s) en attente
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
                  {clientMessages.length > 0 && (
                    <div className="mt-4">
                      <p className="text-sm text-muted-foreground">
                        Dernière réponse: {new Date(clientMessages[0].createdAt).toLocaleString('fr-FR')}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}