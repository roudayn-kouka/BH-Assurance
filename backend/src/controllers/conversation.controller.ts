import { Request, Response } from 'express';
import Conversation from '../models/conversation.model';
import Message from '../models/message.model';
import { computeOpportunityScore } from '../services/opportunity.service';

export const getAllConversations = async (req: Request, res: Response) => {
  try {
    const { client_id, status, completed } = req.query;
    
    const query: any = {};
    if (client_id) query.client_id = client_id;
    if (status) query.status = status;
    if (completed !== undefined) query.is_completed = completed === 'true';
    
    const conversations = await Conversation.find(query)
      .populate('client_id', 'email first_name last_name')
      .sort({ last_activity_at: -1 });
    
    res.json(conversations);
  } catch (error) {
    console.error('Erreur lors de la récupération des conversations:', error);
    res.status(500).json({ error: 'Erreur serveur interne' });
  }
};

export const getConversationById = async (req: Request, res: Response) => {
  try {
    const conversation = await Conversation.findById(req.params.id)
      .populate('client_id', 'email first_name last_name phone');
    
    if (!conversation) {
      return res.status(404).json({ error: 'Conversation non trouvée' });
    }
    
    res.json(conversation);
  } catch (error) {
    console.error('Erreur lors de la récupération de la conversation:', error);
    res.status(500).json({ error: 'Erreur serveur interne' });
  }
};

export const createConversation = async (req: Request, res: Response) => {
  try {
    const { client_id, ...rest } = req.body;
    
    // Vérification si le client existe
    const client = await Client.findById(client_id);
    if (!client) {
      return res.status(404).json({ error: 'Client non trouvé' });
    }
    
    const conversation = new Conversation({
      client_id,
      ...rest
    });
    
    await conversation.save();
    
    // Mise à jour du last_contact_at du client
    await Client.findByIdAndUpdate(client_id, {
      last_contact_at: new Date()
    });
    
    res.status(201).json(conversation);
  } catch (error) {
    console.error('Erreur lors de la création de la conversation:', error);
    res.status(500).json({ error: 'Erreur serveur interne' });
  }
};

export const updateConversation = async (req: Request, res: Response) => {
  try {
    const { status, is_completed } = req.body;
    
    const conversation = await Conversation.findByIdAndUpdate(
      req.params.id,
      { status, is_completed },
      { new: true, runValidators: true }
    );
    
    if (!conversation) {
      return res.status(404).json({ error: 'Conversation non trouvée' });
    }
    
    // Si la conversation est marquée comme terminée, recalculer le score d'opportunité
    if (is_completed) {
      await computeOpportunityScore(conversation.client_id);
    }
    
    res.json(conversation);
  } catch (error) {
    console.error('Erreur lors de la mise à jour de la conversation:', error);
    res.status(500).json({ error: 'Erreur serveur interne' });
  }
};