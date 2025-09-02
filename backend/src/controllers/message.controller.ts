// src/controllers/message.controller.ts

import { Request, Response } from 'express';
import Message from '../models/message.model';
import Conversation from '../models/conversation.model';
import {User} from '../models/user.model'; // ← Import ajouté
import { sendEmail } from '../services/email.service';

/**
 * Créer un nouveau message
 */
export const createMessage = async (req: Request, res: Response) => {
  try {
    const { conversation_id, sender, body, direction } = req.body;
    
    // Vérifier que la conversation existe
    const conversation = await Conversation.findById(conversation_id);
    if (!conversation) {
      return res.status(404).json({ error: 'Conversation non trouvée' });
    }

    // Déterminer le statut initial
    let status: 'open' | 'pending' | 'validated' | 'sent' | 'blocked' = 'open';
    let isClientResponse = false;
    
    if (sender === 'client') {
      status = 'open';
      isClientResponse = true;
      
      // Mettre à jour la conversation
      conversation.last_message_at = new Date();
      conversation.message_count += 1;
      await conversation.save();
    } else if (sender === 'ai') {
      status = 'pending'; // En attente de validation
    } else if (sender === 'agent') {
      status = 'sent';
      
      // Si c'est une réponse de l'agent, envoyer par email
      const client = await User.findById(conversation.client_id);
      if (client && client.email) {
        await sendEmail({
          to: client.email,
          subject: `Réponse à votre demande - ${conversation.subject || 'Conversation'}`,
          text: body
        });
      }
    }

    const message = new Message({
      conversation_id,
      sender,
      body,
      direction,
      status,
      is_client_response: isClientResponse
    });

    await message.save();
    
    // Si c'est un message client, mettre à jour le statut de la conversation
    if (isClientResponse && conversation.status === 'blocked') {
      conversation.status = 'active';
      await conversation.save();
    }

    res.status(201).json(message);
  } catch (error) {
    console.error('Erreur lors de la création du message:', error);
    res.status(500).json({ error: 'Erreur lors de la création du message' });
  }
};

/**
 * Obtenir un message par ID
 */
export const getMessageById = async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const message = await Message.findById(id);
    
    if (!message) {
      return res.status(404).json({ error: 'Message non trouvé' });
    }
    
    res.json(message);
  } catch (error) {
    console.error('Erreur lors du chargement du message:', error);
    res.status(500).json({ error: 'Erreur lors du chargement du message' });
  }
};

/**
 * Obtenir tous les messages d'une conversation
 */
export const getMessagesByConversation = async (req: Request, res: Response) => {
  try {
    const { conversationId } = req.params;
    
    const messages = await Message.find({ conversation_id: conversationId })
      .sort({ created_at: 1 });
    
    res.json(messages);
  } catch (error) {
    console.error('Erreur lors du chargement des messages:', error);
    res.status(500).json({ error: 'Erreur lors du chargement des messages' });
  }
};

/**
 * Valider un message (pour les réponses IA)
 */
export const validateMessage = async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { action, edited_body } = req.body;
    
    const message = await Message.findById(id);
    if (!message) {
      return res.status(404).json({ error: 'Message non trouvé' });
    }
    
    if (message.status !== 'pending') {
      return res.status(400).json({ error: 'Ce message n\'est pas en attente de validation' });
    }
    
    if (action === 'validate') {
      message.status = 'validated';
      if (edited_body) {
        message.body = edited_body;
      }
      await message.save();
      
      // Envoyer le message validé par email
      const conversation = await Conversation.findById(message.conversation_id);
      if (conversation) {
        const client = await User.findById(conversation.client_id);
        if (client && client.email) {
          await sendEmail({
            to: client.email,
            subject: `Réponse à votre demande - ${conversation.subject || 'Conversation'}`,
            text: message.body
          });
          
          // Mettre à jour le statut de la conversation
          conversation.status = 'blocked'; // En attente de réponse client
          await conversation.save();
        }
      }
      
      res.json({ 
        message: 'Message validé et envoyé', 
        ...message 
      });
    } else {
      res.status(400).json({ error: 'Action non reconnue' });
    }
  } catch (error) {
    console.error('Erreur lors de la validation du message:', error);
    res.status(500).json({ error: 'Erreur lors de la validation du message' });
  }
};

/**
 * Mettre à jour le statut d'un message
 */
export const updateMessageStatus = async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { status } = req.body;
    
    const validStatuses: Array<'open' | 'pending' | 'validated' | 'sent' | 'blocked'> = [
      'open', 'pending', 'validated', 'sent', 'blocked'
    ];
    
    if (!validStatuses.includes(status)) {
      return res.status(400).json({ error: 'Statut invalide' });
    }
    
    const message = await Message.findByIdAndUpdate(
      id,
      { status, updated_at: new Date() },
      { new: true }
    );
    
    if (!message) {
      return res.status(404).json({ error: 'Message non trouvé' });
    }
    
    res.json(message);
  } catch (error) {
    console.error('Erreur lors de la mise à jour du statut:', error);
    res.status(500).json({ error: 'Erreur lors de la mise à jour du statut' });
  }
};