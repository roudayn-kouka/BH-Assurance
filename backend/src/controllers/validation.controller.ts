import { Request, Response } from 'express';
import Message from '../models/message.model';
import Client from '../models/client.model';
import Conversation from '../models/conversation.model';

export const getValidationQueue = async (req: Request, res: Response) => {
  try {
    // Récupérer tous les messages en attente de validation
    const pendingMessages = await Message.find({ status: 'pending' })
      .populate('conversation_id', 'client_id status')
      .sort({ created_at: 1 });
    
    // Enrichir avec les informations client
    const queueItems = await Promise.all(pendingMessages.map(async (message) => {
      const conversation = await Conversation.findById(message.conversation_id);
      if (!conversation) return null;
      
      const client = await Client.findById(conversation.client_id);
      if (!client) return null;
      
      return {
        message_id: message._id,
        conversation_id: conversation._id,
        client: {
          id: client._id,
          email: client.email,
          phone: client.phone,
          first_name: client.first_name,
          last_name: client.last_name,
          opportunity_score: client.opportunity_score,
          last_contact_at: client.last_contact_at
        },
        conversation_status: conversation.status,
        subject: message.subject,
        body: message.body,
        created_at: message.created_at
      };
    }));
    
    // Filtrer les éléments null (au cas où)
    const validQueueItems = queueItems.filter(item => item !== null);
    
    res.json(validQueueItems);
  } catch (error) {
    console.error('Erreur lors de la récupération de la file de validation:', error);
    res.status(500).json({ error: 'Erreur serveur interne' });
  }
};