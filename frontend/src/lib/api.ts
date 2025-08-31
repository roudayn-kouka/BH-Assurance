const API_BASE_URL = 'http://localhost:5000/api';

export interface ApiResponse<T> {
  data?: T;
  error?: string;
  status: number;
}

export interface Client {
  id: string;
  // Ajoutez d'autres propriétés Client ici
}

export interface Conversation {
  id: string;
  // Ajoutez d'autres propriétés Conversation ici
}

export interface Message {
  id: string;
  // Ajoutez d'autres propriétés Message ici
}

export async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    const data = await response.json();

    if (!response.ok) {
      return {
        error: data.message || `Erreur HTTP: ${response.status}`,
        status: response.status
      };
    }

    return {
      data,
      status: response.status
    };
  } catch (error) {
    return {
      error: error instanceof Error ? error.message : 'Erreur réseau',
      status: 500
    };
  }
}

// Fonctions spécifiques pour BH Assurance
export const bhAssuranceApi = {
  // Clients
  getClients: () => apiFetch<Client[]>('/clients'),
  getClient: (id: string) => apiFetch<Client>(`/clients/${id}`),

  // Conversations
  getConversations: () => apiFetch<Conversation[]>('/conversations'),
  getConversation: (id: string) => apiFetch<Conversation>(`/conversations/${id}`),

  // Messages
  getMessages: () => apiFetch<Message[]>('/messages'),
  getPendingMessages: () => apiFetch<Message[]>('/messages/pending'),
  validateMessage: (id: string, justification: string) => 
    apiFetch<Message>(`/messages/${id}/validate`, {
      method: 'PATCH',
      body: JSON.stringify({ justification })
    }),

  // Statistiques
  getStats: () => apiFetch<any>('/stats')
};