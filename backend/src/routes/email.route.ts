// src/routes/email.route.ts

import { Router } from 'express';
import { createMessage } from '../controllers/message.controller';
import { User } from '../models/user.model';
import Conversation from '../models/conversation.model'; // ✅ Import ajouté
import Message from '../models/message.model'; // ✅ Import ajouté
import { authenticate } from '../middleware/auth.middleware'; // ✅ Sécurité : uniquement pour admin

const router = Router();

// Appliquer l'authentification
router.use(authenticate);

// Simuler la réception d'un email
router.post('/incoming', async (req, res) => {
  try {
    const { from, to, subject, body, timestamp } = req.body;

    if (!from || !body) {
      return res.status(400).json({ error: 'Les champs "from" et "body" sont requis' });
    }

    // 🔍 Trouver le client par email
    const client = await User.findOne({ email: from });
    if (!client) {
      return res.status(404).json({ error: 'Client non trouvé' });
    }

    // 🔍 Trouver ou créer une conversation
    let conversation = await Conversation.findOne({ client_id: client._id });
    if (!conversation) {
      conversation = new Conversation({
        client_id: client._id,
        subject: subject || 'Nouvelle conversation',
        status: 'active',
        last_activity_at: new Date(timestamp || Date.now()),
        last_message_at: new Date(timestamp || Date.now()),
        message_count: 0,
        opportunity_score: 0
      });
      await conversation.save();
    }

    // 📨 Créer un message "client"
    const message = new Message({
      conversation_id: conversation._id,
      sender: 'client',
      body,
      direction: 'inbox',
      status: 'open',
      is_client_response: true,
      is_modified: false,
      subject: subject || 'Nouveau message',
      created_at: new Date(timestamp || Date.now())
    });

    await message.save();

    // 🔄 Mettre à jour la conversation
    conversation.last_activity_at = new Date(timestamp || Date.now());
    conversation.last_message_at = new Date(timestamp || Date.now());
    conversation.message_count += 1;

    await conversation.save();

    // ✅ Réponse réussie
    res.status(201).json({
      message: 'Email reçu et enregistré avec succès',
      data: {
        message,
        conversation,
        client: {
          id: client._id,
          email: client.email
        }
      }
    });
  } catch (error) {
    console.error('Erreur lors de la réception de l\'email:', error);
    res.status(500).json({ error: 'Erreur serveur interne' });
  }
});

export default router;