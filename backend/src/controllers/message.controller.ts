import { Request, Response } from 'express';
import Message from '../models/message.model';
import Conversation from '../models/conversation.model';
import Client from '../models/client.model';
import { sendValidationNotification } from '../services/email.service';
import Event from '../models/event.model';

export const getMessagesByConversation = async (req: Request, res: Response) => {
  try {
    const messages = await Message.find({ conversation_id: req.params.conversationId })
      .sort({ created_at: 1 });
    
    res.json(messages);
  } catch (error) {
    console.error('Erreur lors de la récupération des messages:', error);
    res.status(500).json({ error: 'Erreur serveur interne' });
  }
};

export const createMessage = async (req: Request, res: Response) => {
  try {
    const { conversation_id, sender, direction, subject, body, status } = req.body;
    
    // Vérification de la conversation
    const conversation = await Conversation.findById(conversation_id);
    if (!conversation) {
      return res.status(404).json({ error: 'Conversation non trouvée' });
    }
    
    // Création du message
    const message = new Message({
      conversation_id,
      sender,
      direction,
      subject,
      body,
      status
    });
    
    await message.save();
    
    // Mise à jour de la conversation
    await Conversation.findByIdAndUpdate(conversation_id, {
      last_activity_at: new Date()
    });
    
    // Mise à jour du last_contact_at du client
    await Client.findByIdAndUpdate(conversation.client_id, {
      last_contact_at: new Date()
    });
    
    // Création d'un événement pour traçabilité
    await Event.create({
      type: 'message_created',
      ref_id: message._id.toString(),
      meta: {
        sender,
        conversation_id,
        status
      }
    });
    
    // Notification si c'est un message de l'IA en attente de validation
    if (sender !== 'client' && status === 'pending') {
      const client = await Client.findById(conversation.client_id).lean();
      await sendValidationNotification(
        message._id.toString(),
        client?.email || 'client inconnu'
      );
    }
    
    res.status(201).json(message);
  } catch (error) {
    console.error('Erreur lors de la création du message:', error);
    res.status(500).json({ error: 'Erreur serveur interne' });
  }
};

export const validateMessage = async (req: Request, res: Response) => {
  try {
    const { action, edited_body, conversation_status, is_completed } = req.body;
    const message = await Message.findById(req.params.id);
    
    if (!message) {
      return res.status(404).json({ error: 'Message non trouvé' });
    }
    
    // Gestion de la validation
    if (action === 'validate') {
      const isModified = edited_body && edited_body !== message.body;
      
      message.status = 'validated';
      if (isModified) {
        message.original_body = message.body;
        message.body = edited_body;
        message.is_modified = true;
      }
      
      message.validated_by = req.user._id;
      message.validated_at = new Date();
      await message.save();
      
      // Mise à jour de la conversation si nécessaire
      if (conversation_status || is_completed !== undefined) {
        await Conversation.findByIdAndUpdate(message.conversation_id, {
          ...(conversation_status && { status: conversation_status }),
          ...(is_completed !== undefined && { is_completed })
        });
      }
      
      // Création d'un événement pour traçabilité
      await Event.create({
        type: 'message_validated',
        ref_id: message._id.toString(),
        meta: {
          validator_id: req.user._id,
          is_modified: isModified,
          previous_status: 'pending'
        }
      });
      
      res.json(message);
    } 
    // Gestion du rejet
    else if (action === 'reject') {
      message.status = 'rejected';
      await message.save();
      
      // Création d'un événement pour traçabilité
      await Event.create({
        type: 'message_rejected',
        ref_id: message._id.toString(),
        meta: {
          validator_id: req.user._id,
          previous_status: 'pending'
        }
      });
      
      res.json(message);
    } 
    else {
      res.status(400).json({ error: 'Action invalide' });
    }
  } catch (error) {
    console.error('Erreur lors de la validation du message:', error);
    res.status(500).json({ error: 'Erreur serveur interne' });
  }
};