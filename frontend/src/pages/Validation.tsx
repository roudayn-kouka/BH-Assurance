// src/app/validation/page.tsx (ou src/components/Validation.tsx)

import { useState, useEffect } from "react"
import { ArrowLeft, CheckCircle, Edit, FileText, Mail, AlertCircle, User, Star, Phone, MapPin, Briefcase, Calendar } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/hooks/use-toast"
import { EmailMessage, generateSubject } from "@/components/EmailMessage"

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
  contrats: string[]
  reponsesNonValidees: ReponseNonValidee[]
}

interface ReponseNonValidee {
  id: string
  contenu: string
  questionClient: string
  timestamp: string
  argumentation: string
}

export default function Validation() {
  const [clients, setClients] = useState<ClientValidation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedClient, setSelectedClient] = useState<ClientValidation | null>(null)
  const [editingResponse, setEditingResponse] = useState<ReponseNonValidee | null>(null)
  const [editedContent, setEditedContent] = useState("")
  const [showArgumentation, setShowArgumentation] = useState<ReponseNonValidee | null>(null)
  const { toast } = useToast()

  // Charger la file de validation depuis l'API
  useEffect(() => {
    const fetchValidationQueue = async () => {
      try {
        const token = localStorage.getItem('token')
        if (!token) throw new Error('Non authentifié')

        const res = await fetch('http://localhost:3001/api/validation/queue', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })

        if (!res.ok) throw new Error('Échec du chargement de la file de validation')

        const apiData = await res.json()

        // Transformer les données API → format frontend
        const formattedClients: ClientValidation[] = apiData.map((item: any) => {
          const client = item.client
          const message = item

          return {
            id: client.id,
            nom: client.last_name || 'Inconnu',
            prenom: client.first_name || 'Inconnu',
            email: client.email,
            telephone: client.phone || 'Non renseigné',
            age: client.age || 0,
            travail: client.job || 'Non renseigné',
            dernierContact: new Date(client.last_contact_at).toLocaleString('fr-TN'),
            scoreOpportunite: client.opportunity_score || 0,
            statusConversation: message.conversation_status,
            contrats: client.contracts?.map((c: any) => `${c.type} ${c.number || c._id}`) || [],
            reponsesNonValidees: [
              {
                id: message.message_id,
                questionClient: message.body, // Supposant que c'est la question
                contenu: message.body, // À remplacer par la réponse IA
                timestamp: new Date(message.created_at).toLocaleString('fr-TN'),
                argumentation: "Réponse générée par l'agent IA basée sur les politiques BH Assurance."
              }
            ]
          }
        })

        setClients(formattedClients)
      } catch (err: any) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    fetchValidationQueue()
  }, [])

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

      if (!res.ok) throw new Error('Échec de validation')

      toast({
        title: "✅ Validé",
        description: "La réponse a été validée et envoyée au client."
      })

      // Mettre à jour l'UI
      setClients(prev => prev.filter(c => c.id !== clientId))
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

      if (!res.ok) throw new Error('Échec de modification')

      toast({
        title: "✅ Modifié et envoyé",
        description: "La réponse modifiée a été envoyée au client."
      })

      setClients(prev => prev.filter(c => c.id !== selectedClient.id))
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

  if (loading) return <div className="p-6">Chargement de la file de validation...</div>
  if (error) return <div className="p-6 text-red-500">Erreur: {error}</div>

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
            Validation - {selectedClient.prenom} {selectedClient.nom}
          </h1>
        </div>

        {/* Informations détaillées du client */}
        <Card className="mb-6 border-l-4 border-l-primary">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Profil Client Complet
            </CardTitle>
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
                    <Badge className={selectedClient.scoreOpportunite >= 80 ? "bg-success" : selectedClient.scoreOpportunite >= 60 ? "bg-accent" : "bg-destructive"}>
                      {selectedClient.scoreOpportunite}/100
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-muted-foreground" />
                    <Badge variant="outline" className="text-xs">
                      {selectedClient.statusConversation}
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

        <div className="space-y-6">
          {selectedClient.reponsesNonValidees.map((reponse) => (
            <Card key={reponse.id} className="border-l-4 border-l-accent">
              <CardHeader>
                <CardTitle className="text-lg flex items-center gap-2">
                  <AlertCircle className="h-5 w-5 text-accent" />
                  Réponse en attente de validation
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  Reçue le {reponse.timestamp}
                </p>
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

                <div className="flex gap-3 pt-4">
                  <Button 
                    onClick={() => handleValider(selectedClient.id, reponse.id)}
                    className="bg-success hover:bg-success/90"
                  >
                    <CheckCircle className="h-4 w-4 mr-2" />
                    Valider
                  </Button>
                  
                  <Dialog>
                    <DialogTrigger asChild>
                      <Button 
                        variant="outline"
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
                          className="bg-success hover:bg-success/90"
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
        Clients avec des réponses en attente de validation, triés par priorité (conversation la plus récente en premier).
      </p>
      
      <div className="grid gap-4">
        {clients.map((client) => (
          <Card 
            key={client.id} 
            className="cursor-pointer hover:shadow-lg transition-shadow border-l-4 border-l-accent"
            onClick={() => setSelectedClient(client)}
          >
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-3">
                  <AlertCircle className="h-5 w-5 text-accent" />
                  {client.prenom} {client.nom}
                </CardTitle>
                <div className="flex items-center gap-2">
                  <Badge className={client.scoreOpportunite >= 80 ? "bg-success" : client.scoreOpportunite >= 60 ? "bg-accent" : "bg-destructive"}>
                    Score: {client.scoreOpportunite}
                  </Badge>
                  <Badge variant="destructive">
                    {client.reponsesNonValidees.length} réponse(s)
                  </Badge>
                </div>
              </div>
              <div className="mt-2">
                <Badge variant="outline" className="text-xs">
                  {client.statusConversation}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
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
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}