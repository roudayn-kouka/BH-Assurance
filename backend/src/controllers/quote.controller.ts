import { Request, Response } from 'express';
import Quote, { IQuote } from '../models/quote.model';
import Conversation from '../models/conversation.model';
import {User} from '../models/user.model';
import { sendQuoteEmail } from '../services/email.service';

// Créer un nouveau devis
export const createQuote = async (req: Request, res: Response) => {
  try {
    const { conversation_id, products, valid_until, notes } = req.body;
    
    // Vérifier que la conversation existe
    const conversation = await Conversation.findById(conversation_id);
    if (!conversation) {
      return res.status(404).json({ error: 'Conversation non trouvée' });
    }
    
    // Vérifier que le client existe
    const client = await User.findById(conversation.client_id);
    if (!client) {
      return res.status(404).json({ error: 'Client non trouvé' });
    }
    
    // Calculer la date d'expiration si non fournie
    const validUntil = valid_until ? new Date(valid_until) : new Date(Date.now() + 15 * 24 * 60 * 60 * 1000);
    
    const quote = new Quote({
      conversation_id,
      client_id: conversation.client_id,
      products,
      valid_until: validUntil,
      notes,
      status: 'draft'
    });
    
    await quote.save();
    
    res.status(201).json(quote);
  } catch (error) {
    res.status(500).json({ error: 'Erreur lors de la création du devis' });
  }
};

// Envoyer un devis par email
export const sendQuote = async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    
    const quote = await Quote.findById(id).populate('client_id');
    if (!quote) {
      return res.status(404).json({ error: 'Devis non trouvé' });
    }
    
    const client = await User.findById(quote.client_id);
    if (!client) {
      return res.status(404).json({ error: 'Client non trouvé' });
    }
    
    // Envoyer l'email
    const emailSent = await sendQuoteEmail(quote, client);
    
    if (emailSent) {
      // Mettre à jour le statut du devis
      quote.status = 'sent';
      await quote.save();
      
      res.json({
        message: 'Devis envoyé avec succès',
        quote
      });
    } else {
      res.status(500).json({ error: 'Erreur lors de l\'envoi du devis par email' });
    }
  } catch (error) {
    res.status(500).json({ error: 'Erreur lors de l\'envoi du devis' });
  }
};

// Mettre à jour le statut du devis
export const updateQuoteStatus = async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    const { status } = req.body;
    
    const validStatuses: IQuote['status'][] = ['draft', 'sent', 'accepted', 'rejected', 'expired'];
    if (!validStatuses.includes(status)) {
      return res.status(400).json({ error: 'Statut invalide' });
    }
    
    const quote = await Quote.findByIdAndUpdate(
      id,
      { status, updated_at: new Date() },
      { new: true }
    );
    
    if (!quote) {
      return res.status(404).json({ error: 'Devis non trouvé' });
    }
    
    // Si le devis est accepté, mettre à jour la conversation
    if (status === 'accepted') {
      const conversation = await Conversation.findById(quote.conversation_id);
      if (conversation) {
        conversation.status = 'success';
        conversation.completion_reason = 'Devis accepté';
        conversation.is_completed = true;
        await conversation.save();
      }
    }
    
    res.json(quote);
  } catch (error) {
    res.status(500).json({ error: 'Erreur lors de la mise à jour du statut du devis' });
  }
};

// Obtenir un devis par ID
export const getQuoteById = async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    
    const quote = await Quote.findById(id)
      .populate('client_id', 'first_name last_name email')
      .populate('conversation_id');
    
    if (!quote) {
      return res.status(404).json({ error: 'Devis non trouvé' });
    }
    
    res.json(quote);
  } catch (error) {
    res.status(500).json({ error: 'Erreur lors du chargement du devis' });
  }
};

// Obtenir les devis d'une conversation
export const getQuotesByConversation = async (req: Request, res: Response) => {
  try {
    const { conversationId } = req.params;
    
    const quotes = await Quote.find({ conversation_id: conversationId })
      .populate('client_id', 'first_name last_name email')
      .sort({ created_at: -1 });
    
    res.json(quotes);
  } catch (error) {
    res.status(500).json({ error: 'Erreur lors du chargement des devis' });
  }
};