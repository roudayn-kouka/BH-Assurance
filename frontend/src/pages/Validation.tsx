// src/app/validation/page.tsx

import { useState, useEffect, useRef } from "react"
import { ArrowLeft, CheckCircle, Edit, FileText, Mail, AlertCircle, User, Star, Phone, MapPin, Briefcase, Calendar, Bell, BellRing, RefreshCw, TrendingUp, TrendingDown, ChevronDown, ChevronUp, File, Send, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/hooks/use-toast"
import { EmailMessage, generateSubject } from "@/components/EmailMessage"
import { ConversationStatusBadge, MessageStatusBadge } from "@/components/conversation-status-badge"
import { QuoteBuilder } from "@/components/quote-builder"
import { QuoteCard } from "@/components/quote-card"

// Types
interface ClientValidation {
  id: string
  nom: string
  prenom: string
  email: string
  telephone: string
  age: number
  travail: string
  dernierContact: string
  scoreOpportunite: number
  statusConversation: 
    | "nouvelle_opportunite"
    | "renouvellement"
    | "upsell_cross_sell"
    | "resiliation"
    | "reclamation"
    | "support_information"
    | "prospect_froid"
    | "perte_client"
    | "success"
  contrats: string[]
  reponsesNonValidees: ReponseNonValidee[]
  isCompleted: boolean
  completionReason?: string
  quotes: Quote[]
}

interface Quote {
  id: string
  products: {
    name: string
    description: string
    price: number
    quantity: number
  }[]
  total_amount: number
  valid_until: string
  status: string
  created_at: string
  notes?: string
}

interface ReponseNonValidee {
  id: string
  contenu: string
  questionClient: string
  timestamp: string
  argumentation: string
  status: 'open' | 'pending' | 'validated' | 'sent' | 'blocked'
  conversationId: string
}

export default function Validation() {
  const [clients, setClients] = useState<ClientValidation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedClient, setSelectedClient] = useState<ClientValidation | null>(null)
  const [editingResponse, setEditingResponse] = useState<ReponseNonValidee | null>(null)
  const [editedContent, setEditedContent] = useState("")
  const [showArgumentation, setShowArgumentation] = useState<ReponseNonValidee | null>(null)
  const [notificationEnabled, setNotificationEnabled] = useState(false)
  const [showNotifications, setShowNotifications] = useState(false)
  const [pendingValidations, setPendingValidations] = useState(0)
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null)
  const { toast } = useToast()
  const notificationSound = useRef<HTMLAudioElement | null>(null)

  // Initialiser le son de notification
  useEffect(() => {
    notificationSound.current = new Audio('/notification-sound.mp3')
    return () => {
      if (notificationSound.current) {
        notificationSound.current = null
      }
    }
  }, [])

  // Charger la file de validation depuis l'API
  const fetchValidationQueue = async () => {
    try {
      const token = localStorage.getItem('token')
      if (!token) throw new Error('Non authentifié')

      const res = await fetch('http://localhost:3001/api/validation/queue', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.error || 'Échec du chargement de la file de validation')
      }

      const apiData = await res.json()

      // Transformer les données API → format frontend
      const formattedClients: ClientValidation[] = apiData.map((item: any) => {
        const client = item.client
        const message = item.message

        return {
          id: client._id,
          nom: client.last_name || 'Inconnu',
          prenom: client.first_name || 'Inconnu',
          email: client.email,
          telephone: client.phone || 'Non renseigné',
          age: client.age || 0,
          travail: client.job || 'Non renseigné',
          dernierContact: new Date(client.last_contact_at).toLocaleString('fr-TN'),
          scoreOpportunite: client.opportunity_score || 0,
          statusConversation: client.conversation_status,
          contrats: client.contracts?.map((c: any) => `${c.type} ${c.number || c._id}`) || [],
          reponsesNonValidees: [
            {
              id: message._id,
              questionClient: message.body,
              contenu: message.body,
              timestamp: new Date(message.created_at).toLocaleString('fr-TN'),
              argumentation: message.argumentation || "Réponse générée par l'agent IA basée sur les politiques BH Assurance.",
              status: message.status,
              conversationId: message.conversation_id
            }
          ],
          isCompleted: client.is_completed,
          completionReason: client.completion_reason,
          quotes: []
        }
      })

      setClients(formattedClients)
      setPendingValidations(formattedClients.length)
      
      // Jouer un son de notification si de nouvelles validations sont disponibles
      if (formattedClients.length > 0 && notificationEnabled) {
        playNotificationSound()
        showBrowserNotification()
      }
    } catch (err: any) {
      setError(err.message)
    }
  }

  // Activer/désactiver les notifications
  const toggleNotification = () => {
    if (!notificationEnabled) {
      // Demander la permission pour les notifications navigateur
      if ('Notification' in window) {
        Notification.requestPermission().then(permission => {
          if (permission === 'granted') {
            setNotificationEnabled(true)
            toast({
              title: "Notifications activées",
              description: "Vous recevrez des alertes pour les nouvelles validations."
            })
            
            // Démarrer le polling
            startPolling()
          }
        })
      } else {
        toast({
          title: "Erreur",
          description: "Les notifications navigateur ne sont pas supportées",
          variant: "destructive"
        })
      }
    } else {
      setNotificationEnabled(false)
      stopPolling()
      toast({
        title: "Notifications désactivées",
        description: "Vous ne recevrez plus d'alertes pour les nouvelles validations."
      })
    }
  }

  // Démarrer le polling
  const startPolling = () => {
    if (pollingInterval) clearInterval(pollingInterval)
    
    const interval = setInterval(() => {
      fetchValidationQueue()
    }, 30000) // Vérifie toutes les 30 secondes
    
    setPollingInterval(interval)
  }

  // Arrêter le polling
  const stopPolling = () => {
    if (pollingInterval) {
      clearInterval(pollingInterval)
      setPollingInterval(null)
    }
  }

  // Jouer le son de notification
  const playNotificationSound = () => {
    if (notificationSound.current) {
      notificationSound.current.play().catch(e => console.log('Erreur de lecture du son:', e))
    }
  }

  // Afficher une notification navigateur
  const showBrowserNotification = () => {
    if (Notification.permission === 'granted') {
      new Notification('Nouvelle validation requise', {
        body: 'Un message client nécessite votre validation',
        icon: '/bh-logo.png'
      })
    }
  }

  // Charger les devis pour un client
  const loadQuotesForClient = async (clientId: string) => {
    try {
      const token = localStorage.getItem('token')
      if (!token) return

      const res = await fetch(`http://localhost:3001/api/quotes?client_id=${clientId}`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!res.ok) throw new Error('Échec du chargement des devis')

      const quotes = await res.json()
      
      setClients(prev => prev.map(client => 
        client.id === clientId ? { ...client, quotes } : client
      ))
    } catch (err) {
      console.error('Erreur chargement devis:', err)
    }
  }

  // Créer un devis
  const handleCreateQuote = async (quoteData: any) => {
    try {
      const token = localStorage.getItem('token')
      if (!token) return

      const res = await fetch('http://localhost:3001/api/quotes', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(quoteData)
      })

      if (!res.ok) throw new Error('Échec de création du devis')

      const quote = await res.json()
      
      // Mettre à jour le client avec le nouveau devis
      setClients(prev => prev.map(client => 
        client.id === quoteData.client_id ? { 
          ...client, 
          quotes: [quote, ...client.quotes] 
        } : client
      ))
      
      toast({
        title: "✅ Devis créé",
        description: "Le devis a été créé avec succès."
      })
    } catch (err: any) {
      toast({
        title: "❌ Échec",
        description: err.message,
        variant: "destructive"
      })
    }
  }

  // Envoyer un devis
  const handleSendQuote = async (quoteId: string) => {
    try {
      const token = localStorage.getItem('token')
      if (!token) return

      const res = await fetch(`http://localhost:3001/api/quotes/${quoteId}/send`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })

      if (!res.ok) throw new Error('Échec d\'envoi du devis')

      const quote = await res.json()
      
      // Mettre à jour le devis dans l'UI
      setClients(prev => prev.map(client => ({
        ...client,
        quotes: client.quotes.map(q => q.id === quoteId ? quote : q)
      })))
      
      toast({
        title: "✅ Devis envoyé",
        description: "Le devis a été envoyé au client par email."
      })
    } catch (err: any) {
      toast({
        title: "❌ Échec",
        description: err.message,
        variant: "destructive"
      })
    }
  }

  // Valider un message
  const handleValider = async (clientId: string, messageId: string) => {
    try {
      const token = localStorage.getItem('token')
      if (!token) return

      const res = await fetch(`http://localhost:3001/api/messages/${messageId}/validate`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ action: 'validate' })
      })

      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.error || 'Échec de validation')
      }

      toast({
        title: "✅ Validé",
        description: "La réponse a été validée et envoyée au client."
      })

      // Mettre à jour l'UI
      setClients(prev => {
        const updatedClients = prev.filter(c => c.id !== clientId)
        setPendingValidations(updatedClients.length)
        return updatedClients
      })
      
      if (selectedClient?.id === clientId) {
        setSelectedClient(null)
      }
    } catch (err: any) {
      toast({
        title: "❌ Échec",
        description: err.message,
        variant: "destructive"
      })
    }
  }

  // Modifier un message
  const handleModifier = (response: ReponseNonValidee) => {
    setEditingResponse(response)
    setEditedContent(response.contenu)
  }

  // Confirmer modification
  const handleConfirmerModification = async () => {
    if (!editingResponse || !selectedClient) return

    try {
      const token = localStorage.getItem('token')
      const res = await fetch(`http://localhost:3001/api/messages/${editingResponse.id}/validate`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          action: 'validate',
          edited_body: editedContent
        })
      })

      if (!res.ok) {
        const errorData = await res.json()
        throw new Error(errorData.error || 'Échec de modification')
      }

      toast({
        title: "✅ Modifié et envoyé",
        description: "La réponse modifiée a été envoyée au client."
      })

      setClients(prev => {
        const updatedClients = prev.filter(c => c.id !== selectedClient.id)
        setPendingValidations(updatedClients.length)
        return updatedClients
      })
      
      setEditingResponse(null)
      setEditedContent("")
      
      if (selectedClient) setSelectedClient(null)
    } catch (err: any) {
      toast({
        title: "❌ Échec",
        description: err.message,
        variant: "destructive"
      })
    }
  }

  // Initialiser le chargement
  useEffect(() => {
    fetchValidationQueue()
    
    // Nettoyer le polling à la déconnexion
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval)
      }
    }
  }, [])

  // Gestion des notifications
  useEffect(() => {
    if (notificationEnabled) {
      startPolling()
    } else {
      stopPolling()
    }
    
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval)
      }
    }
  }, [notificationEnabled])

  if (loading) return <div className="p-6">Chargement de la file de validation...</div>
  if (error) return <div className="p-6 text-red-500">Erreur: {error}</div>

  if (selectedClient) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <Button 
              variant="outline" 
              onClick={() => setSelectedClient(null)}
              className="flex items-center gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Retour à la liste
            </Button>
            <h1 className="text-2xl font-bold text-primary">
              Validation - {selectedClient.prenom} {selectedClient.nom}
            </h1>
          </div>
          
          <div className="flex items-center gap-3">
            <Button 
              variant="outline" 
              size="icon"
              onClick={() => loadQuotesForClient(selectedClient.id)}
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
            
            <Button 
              variant="outline"
              onClick={toggleNotification}
            >
              {notificationEnabled ? (
                <BellRing className="h-4 w-4 mr-2" />
              ) : (
                <Bell className="h-4 w-4 mr-2" />
              )}
              {notificationEnabled ? "Notifications activées" : "Activer les notifications"}
            </Button>
          </div>
        </div>

        {/* Informations détaillées du client */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          <Card className="lg:col-span-2 border-l-4 border-l-primary">
            <CardHeader>
              <div className="flex justify-between items-start">
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5" />
                  Profil Client Complet
                </CardTitle>
                <div className="flex items-center gap-2">
                  <ConversationStatusBadge 
                    status={selectedClient.statusConversation} 
                    isCompleted={selectedClient.isCompleted} 
                  />
                  {selectedClient.completionReason && (
                    <Badge variant="outline" className="text-xs">
                      {selectedClient.completionReason}
                    </Badge>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                <div className="space-y-4">
                  <h4 className="font-semibold text-primary">Informations Personnelles</h4>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">{selectedClient.prenom} {selectedClient.nom}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">{selectedClient.age} ans</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Briefcase className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">{selectedClient.travail}</span>
                    </div>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <h4 className="font-semibold text-primary">Contact</h4>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Mail className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">{selectedClient.email}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Phone className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">{selectedClient.telephone}</span>
                    </div>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <h4 className="font-semibold text-primary">Score & Statut</h4>
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Star className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">Score d'Opportunité: </span>
                      <Badge className={
                        selectedClient.scoreOpportunite >= 80 ? "bg-success" : 
                        selectedClient.scoreOpportunite >= 60 ? "bg-accent" : "bg-destructive"
                      }>
                        {selectedClient.scoreOpportunite}/100
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <TrendingUp className="h-4 w-4 text-muted-foreground" />
                      <span className="text-sm">Potentiel de conversion: </span>
                      <Badge className={
                        selectedClient.scoreOpportunite >= 80 ? "bg-success" : 
                        selectedClient.scoreOpportunite >= 60 ? "bg-accent" : "bg-destructive"
                      }>
                        {selectedClient.scoreOpportunite >= 80 ? "Élevé" : 
                         selectedClient.scoreOpportunite >= 60 ? "Moyen" : "Faible"}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-muted-foreground" />
                      <Badge variant="outline" className="text-xs">
                        {selectedClient.statusConversation.replace('_', ' ')}
                      </Badge>
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="mt-6">
                <h4 className="font-semibold text-primary mb-3">Contrats Actuels</h4>
                <div className="flex flex-wrap gap-2">
                  {selectedClient.contrats.map((contrat, index) => (
                    <Badge key={index} variant="outline" className="text-xs">
                      {contrat}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-primary" />
                Analyse de Performance
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-sm">Potentiel commercial</span>
                    <span className="font-bold">{selectedClient.scoreOpportunite}%</span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div 
                      className={`h-full ${selectedClient.scoreOpportunite >= 80 ? 'bg-success' : selectedClient.scoreOpportunite >= 60 ? 'bg-accent' : 'bg-destructive'}`}
                      style={{ width: `${selectedClient.scoreOpportunite}%` }}
                    ></div>
                  </div>
                </div>
                
                <div className="border-t pt-4">
                  <h4 className="font-semibold mb-2">Statut de la conversation</h4>
                  <ConversationStatusBadge 
                    status={selectedClient.statusConversation} 
                    isCompleted={selectedClient.isCompleted} 
                  />
                  {selectedClient.completionReason && (
                    <p className="text-xs text-muted-foreground mt-1">
                      {selectedClient.completionReason}
                    </p>
                  )}
                </div>
                
                <div className="border-t pt-4">
                  <h4 className="font-semibold mb-2">Actions rapides</h4>
                  <div className="grid grid-cols-2 gap-2">
                    <Button 
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        // Ouvrir le dashboard d'analyse
                        window.open('/analytics', '_blank')
                      }}
                    >
                      <TrendingUp className="h-4 w-4 mr-1" />
                      Analyse
                    </Button>
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button variant="outline" size="sm">
                          <File className="h-4 w-4 mr-1" />
                          Devis
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="max-w-3xl">
                        <DialogHeader>
                          <DialogTitle>Créer un devis</DialogTitle>
                          <DialogDescription>
                            Configurez les produits et le prix pour ce client
                          </DialogDescription>
                        </DialogHeader>
                        <QuoteBuilder 
                          clientId={selectedClient.id}
                          conversationId={selectedClient.reponsesNonValidees[0]?.conversationId}
                          onSubmit={handleCreateQuote}
                        />
                      </DialogContent>
                    </Dialog>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Devis */}
        {selectedClient.quotes.length > 0 && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <File className="h-5 w-5" />
                Devis
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {selectedClient.quotes.map(quote => (
                  <QuoteCard 
                    key={quote.id}
                    quote={quote}
                    onSend={() => handleSendQuote(quote.id)}
                    onAccept={async () => {
                      // Mettre à jour le statut de la conversation
                      try {
                        const token = localStorage.getItem('token');
                        const res = await fetch(`http://localhost:3001/api/conversations/${selectedClient.reponsesNonValidees[0].conversationId}/complete`, {
                          method: 'POST',
                          headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                          },
                          body: JSON.stringify({ reason: 'success' })
                        });
                        
                        if (!res.ok) throw new Error('Échec de la mise à jour');
                        
                        const updatedClient = {
                          ...selectedClient,
                          isCompleted: true,
                          completionReason: 'success'
                        };
                        setSelectedClient(updatedClient);
                        
                        toast({
                          title: "✅ Succès",
                          description: "La conversation a été marquée comme réussie."
                        });
                      } catch (err) {
                        toast({
                          title: "❌ Échec",
                          description: "Impossible de mettre à jour le statut de la conversation.",
                          variant: "destructive"
                        });
                      }
                    }}
                    onReject={async () => {
                      // Mettre à jour le statut de la conversation
                      try {
                        const token = localStorage.getItem('token');
                        const res = await fetch(`http://localhost:3001/api/conversations/${selectedClient.reponsesNonValidees[0].conversationId}/complete`, {
                          method: 'POST',
                          headers: {
                            'Authorization': `Bearer ${token}`,
                            'Content-Type': 'application/json'
                          },
                          body: JSON.stringify({ reason: 'failed' })
                        });
                        
                        if (!res.ok) throw new Error('Échec de la mise à jour');
                        
                        const updatedClient = {
                          ...selectedClient,
                          isCompleted: true,
                          completionReason: 'failed'
                        };
                        setSelectedClient(updatedClient);
                        
                        toast({
                          title: "✅ Mis à jour",
                          description: "La conversation a été marquée comme échouée."
                        });
                      } catch (err) {
                        toast({
                          title: "❌ Échec",
                          description: "Impossible de mettre à jour le statut de la conversation.",
                          variant: "destructive"
                        });
                      }
                    }}
                  />
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        <div className="space-y-6">
          {selectedClient.reponsesNonValidees.map((reponse) => (
            <Card key={reponse.id} className="border-l-4 border-l-accent">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <AlertCircle className="h-5 w-5 text-accent" />
                      Réponse en attente de validation
                    </CardTitle>
                    <p className="text-sm text-muted-foreground">
                      Reçue le {reponse.timestamp}
                    </p>
                  </div>
                  <MessageStatusBadge status={reponse.status} />
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-4">
                  <div>
                    <h4 className="font-medium text-bh-navy mb-2">Question du client :</h4>
                    <EmailMessage
                      from={`${selectedClient.prenom} ${selectedClient.nom}`}
                      fromEmail={selectedClient.email}
                      to="Agent IA BH Assurance"
                      toEmail="support@bh-assurance.tn"
                      subject={generateSubject("question", reponse.questionClient)}
                      date={reponse.timestamp}
                      body={reponse.questionClient}
                      direction="inbox"
                      tag="Question"
                    />
                  </div>
                  
                  <div>
                    <h4 className="font-medium text-bh-navy mb-2">Réponse de l'agent IA (en attente de validation) :</h4>
                    <EmailMessage
                      from="Agent IA BH Assurance"
                      fromEmail="support@bh-assurance.tn"
                      to={`${selectedClient.prenom} ${selectedClient.nom}`}
                      toEmail={selectedClient.email}
                      subject="Réponse de BH Assurance à votre demande"
                      date={reponse.timestamp}
                      body={reponse.contenu}
                      direction="sent"
                      tag="Réponse en attente"
                    />
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row gap-3 pt-4">
                  <Button 
                    onClick={() => handleValider(selectedClient.id, reponse.id)}
                    className="bg-success hover:bg-success/90 flex-1"
                  >
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Valider
                  </Button>
                  
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button 
                        variant="outline"
                        className="flex-1"
                        onClick={() => handleModifier(reponse)}
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
                          className="bg-success hover:bg-success/90 w-full sm:w-auto"
                        >
                          <Mail className="h-4 w-4 mr-2" />
                          Confirmer et envoyer
                        </Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>

                  <Dialog>
                    <DialogTrigger asChild>
                      <Button 
                        variant="outline"
                        className="flex-1"
                        onClick={() => setShowArgumentation(reponse)}
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
                          {reponse.argumentation}
                        </p>
                      </div>
                    </DialogContent>
                  </Dialog>
                  
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button 
                        variant="outline"
                        className="flex-1 text-bh-navy border-bh-navy"
                      >
                        <File className="h-4 w-4 mr-2" />
                        Créer un devis
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="max-w-3xl">
                      <DialogHeader>
                        <DialogTitle>Créer un devis</DialogTitle>
                        <DialogDescription>
                          Configurez les produits et le prix pour ce client
                        </DialogDescription>
                      </DialogHeader>
                      <QuoteBuilder 
                        clientId={selectedClient.id}
                        conversationId={reponse.conversationId}
                        onSubmit={handleCreateQuote}
                      />
                    </DialogContent>
                  </Dialog>
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
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-primary">Validation des réponses</h1>
          <p className="text-muted-foreground mt-2">
            Clients avec des réponses en attente de validation, triés par priorité (conversation la plus récente en premier).
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <Badge variant="destructive" className="px-3 py-1">
            {pendingValidations} en attente
          </Badge>
          
          <Button 
            variant={notificationEnabled ? "default" : "outline"}
            onClick={toggleNotification}
          >
            {notificationEnabled ? (
              <BellRing className="h-4 w-4 mr-2" />
            ) : (
              <Bell className="h-4 w-4 mr-2" />
            )}
            {notificationEnabled ? "Notifications activées" : "Activer les notifications"}
          </Button>
        </div>
      </div>
      
      {showNotifications && pendingValidations > 0 && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Notifications
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <p className="text-sm">
                {pendingValidations} nouvelle{pendingValidations > 1 ? 's' : ''} validation{pendingValidations > 1 ? 's' : ''} requise{pendingValidations > 1 ? 's' : ''}.
              </p>
              <Button 
                variant="outline"
                size="sm"
                onClick={() => {
                  fetchValidationQueue()
                  setShowNotifications(false)
                }}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Actualiser
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
      
      <div className="grid gap-4">
        {clients.map((client) => (
          <Card 
            key={client.id} 
            className="cursor-pointer hover:shadow-lg transition-shadow border-l-4 border-l-accent"
            onClick={() => {
              setSelectedClient(client)
              loadQuotesForClient(client.id)
            }}
          >
            <CardHeader>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <AlertCircle className="h-5 w-5 text-accent" />
                  <div>
                    <h3 className="font-bold">{client.prenom} {client.nom}</h3>
                    <p className="text-xs text-muted-foreground">{client.email}</p>
                  </div>
                </div>
                
                <div className="flex flex-col sm:flex-row sm:items-center gap-2">
                  <div className="flex items-center gap-2">
                    <Badge className={
                      client.scoreOpportunite >= 80 ? "bg-success" : 
                      client.scoreOpportunite >= 60 ? "bg-accent" : "bg-destructive"
                    }>
                      {client.scoreOpportunite}%
                    </Badge>
                    <Badge variant="destructive">
                      {client.reponsesNonValidees.length} réponse{client.reponsesNonValidees.length > 1 ? 's' : ''}
                    </Badge>
                  </div>
                  <ConversationStatusBadge 
                    status={client.statusConversation} 
                    isCompleted={client.isCompleted} 
                  />
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
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
                <div>
                  <p className="text-muted-foreground">Travail</p>
                  <p className="font-medium">{client.travail}</p>
                </div>
              </div>
              
              {client.quotes.length > 0 && (
                <div className="mt-4 pt-4 border-t">
                  <div className="flex items-center gap-2 mb-2">
                    <File className="h-4 w-4 text-primary" />
                    <span className="font-medium">Devis:</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {client.quotes.slice(0, 3).map((quote, index) => (
                      <Badge key={index} variant="outline" className="text-xs">
                        {quote.total_amount.toFixed(2)} DT - {quote.status}
                      </Badge>
                    ))}
                    {client.quotes.length > 3 && (
                      <Badge variant="outline" className="text-xs">
                        +{client.quotes.length - 3} autres
                      </Badge>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
        
        {clients.length === 0 && !loading && (
          <Card className="text-center py-12">
            <CardContent>
              <Bell className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-xl font-semibold mb-2">Aucune validation requise</h3>
              <p className="text-muted-foreground mb-4">
                Toutes les réponses ont été validées. Vous recevrez une notification dès qu'un nouveau message nécessitera votre attention.
              </p>
              <Button 
                variant="outline"
                onClick={fetchValidationQueue}
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Actualiser manuellement
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}