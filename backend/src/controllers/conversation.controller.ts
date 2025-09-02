// src/controllers/conversation.controller.ts

import { Request, Response } from 'express';
import Conversation from '../models/conversation.model';
import Message from '../models/message.model';
import {User} from '../models/user.model';

/**
 * Marquer une conversation comme terminée
 */
export const completeConversation = async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { reason } = req.body;
    
    const validReasons = ['success', 'failed', 'resiliation', 'new_opportunity', 'upsell_cross_sell'];
    if (!reason || !validReasons.includes(reason)) {
      return res.status(400).json({ error: 'Raison invalide' });
    }
    
    const conversation = await Conversation.findById(id);
    if (!conversation) {
      return res.status(404).json({ error: 'Conversation non trouvée' });
    }
    
    conversation.is_completed = true;
    conversation.status = 'completed';
    conversation.completion_reason = reason;
    
    await conversation.save();
    
    res.json({
      message: 'Conversation marquée comme terminée',
      conversation
    });
  } catch (error) {
    console.error('Erreur dans completeConversation:', error);
    res.status(500).json({ error: 'Erreur lors de la finalisation de la conversation' });
  }
};

/**
 * Obtenir les conversations avec filtre par statut
 */
export const getConversations = async (req: Request, res: Response) => {
  try {
    const { client_id, status, is_completed } = req.query;
    const filter: any = {};
    
    if (client_id) filter.client_id = client_id;
    if (status) filter.status = status;
    if (is_completed !== undefined) filter.is_completed = is_completed === 'true';
    
    const conversations = await Conversation.find(filter)
      .populate('client_id', 'first_name last_name email phone')
      .sort({ last_message_at: -1 });
    
    res.json(conversations);
  } catch (error) {
    console.error('Erreur dans getConversations:', error);
    res.status(500).json({ error: 'Erreur lors du chargement des conversations' });
  }
};

/**
 * Obtenir une conversation par ID
 */
export const getConversationById = async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    
    const conversation = await Conversation.findById(id)
      .populate('client_id', 'first_name last_name email phone')
      .populate('messages');
    
    if (!conversation) {
      return res.status(404).json({ error: 'Conversation non trouvée' });
    }
    
    res.json(conversation);
  } catch (error) {
    console.error('Erreur dans getConversationById:', error);
    res.status(500).json({ error: 'Erreur lors du chargement de la conversation' });
  }
};

/**
 * Créer une nouvelle conversation
 */
export const createConversation = async (req: Request, res: Response) => {
  try {
    const { client_id, subject, status } = req.body;
    
    if (!client_id) {
      return res.status(400).json({ error: 'client_id est requis' });
    }

    const client = await User.findById(client_id);
    if (!client) {
      return res.status(404).json({ error: 'Client non trouvé' });
    }

    const conversation = new Conversation({
      client_id,
      subject: subject || 'Nouvelle conversation',
      status: status || 'active'
    });

    await conversation.save();

    res.status(201).json(conversation);
  } catch (error) {
    console.error('Erreur dans createConversation:', error);
    res.status(500).json({ error: 'Erreur lors de la création de la conversation' });
  }
};