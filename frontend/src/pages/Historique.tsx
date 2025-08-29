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
        const response = await fetch("http://localhost:5000/api/clients")

        if (!response.ok) {
          throw new Error(`Erreur HTTP: ${response.status}`)
        }

        const data = await response.json()
        // ✅ Toujours transformer en tableau
        const clientList = Array.isArray(data) ? data : data.clients || []
        setClients(clientList)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur de chargement")
        console.error("Erreur fetch clients:", err)

        // Fallback vers les données mockées
        setClients([
          {
            _id: "1",
            nom: "Sarra Mabrouk",
            email: "sarra.mabrouk@gmail.com",
            telephone: "+216 22 345 678",
            statut: "actif",
          },
          {
            _id: "2",
            nom: "Karim Sassi",
            email: "karim.sassi@gmail.com",
            telephone: "+216 98 123 456",
            statut: "actif",
          },
          {
            _id: "3",
            nom: "Ahmed Ben Ali",
            email: "ahmed.benali@email.com",
            telephone: "+216 20 123 456",
            statut: "actif",
          },
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
        const response = await fetch("http://localhost:5000/api/conversations")

        if (!response.ok) {
          throw new Error(`Erreur HTTP: ${response.status}`)
        }

        const data = await response.json()
        const convList = Array.isArray(data) ? data : data.conversations || []
        const clientConversations = convList.filter(
          (conv: Conversation) => conv.clientId === selectedClient._id
        )
        setConversations(clientConversations)
        setError(null)
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Erreur de chargement des conversations"
        )
        console.error("Erreur fetch conversations:", err)
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
      const response = await fetch("http://localhost:5000/api/messages/pending")

      if (!response.ok) {
        throw new Error(`Erreur HTTP: ${response.status}`)
      }

      const data = await response.json()
      const msgList = Array.isArray(data) ? data : data.messages || []

      // Simulation: filtre temporaire
      const clientMessages = msgList.filter(
        (msg: Message) => msg.conversationId === "1"
      )
      setMessages(clientMessages)
      setError(null)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Erreur de chargement des messages"
      )
      console.error("Erreur fetch messages:", err)
    } finally {
      setLoading(false)
    }
  }

  // 🟢 ... (tout le rendu de ton JSX reste identique)

  return (
    <div className="p-6">
      {/* … ton JSX déjà écrit … */}
    </div>
  )
}