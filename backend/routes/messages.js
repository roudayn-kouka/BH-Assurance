const express = require('express');
const router = express.Router();
const Message = require('../models/Messages');
const Conversation = require('../models/Conversation');
const Client = require('../models/Client');

// GET /api/messages - Récupérer tous les messages
router.get('/', async (req, res) => {
  try {
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 10;
    const skip = (page - 1) * limit;
    const { statut, expediteur } = req.query;
    
    let filter = {};
    if (statut) filter.statut = statut;
    if (expediteur) filter.expediteur = expediteur;
    
    const messages = await Message.find(filter)
      .populate({
        path: 'conversationId',
        populate: {
          path: 'clientId',
          select: 'nom email telephone'
        }
      })
      .sort({ createdAt: -1 })
      .skip(skip)
      .limit(limit);
    
    const total = await Message.countDocuments(filter);
    
    res.json({
      messages,
      currentPage: page,
      totalPages: Math.ceil(total / limit),
      totalMessages: total
    });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

// GET /api/messages/pending - Récupérer les messages en attente de validation
router.get('/pending', async (req, res) => {
  try {
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 10;
    const skip = (page - 1) * limit;
    
    const messages = await Message.find({ 
      statut: 'en_attente',
      expediteur: 'agent'
    })
      .populate({
        path: 'conversationId',
        populate: {
          path: 'clientId',
          select: 'nom email telephone'
        }
      })
      .sort({ createdAt: -1 })
      .skip(skip)
      .limit(limit);
    
    const total = await Message.countDocuments({ 
      statut: 'en_attente',
      expediteur: 'agent'
    });
    
    res.json({
      messages,
      currentPage: page,
      totalPages: Math.ceil(total / limit),
      totalPending: total
    });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

// GET /api/messages/:id - Récupérer un message par ID
router.get('/:id', async (req, res) => {
  try {
    const message = await Message.findById(req.params.id)
      .populate({
        path: 'conversationId',
        populate: {
          path: 'clientId',
          select: 'nom email telephone'
        }
      });
    
    if (!message) {
      return res.status(404).json({ message: 'Message non trouvé' });
    }
    
    res.json(message);
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

// PATCH /api/messages/:id/validate - Valider un message
router.patch('/:id/validate', async (req, res) => {
  try {
    const { justification } = req.body;
    
    const message = await Message.findById(req.params.id)
      .populate({
        path: 'conversationId',
        populate: {
          path: 'clientId',
          select: 'nom email telephone'
        }
      });
    
    if (!message) {
      return res.status(404).json({ message: 'Message non trouvé' });
    }

    // Envoyer l'email (simulation)
    console.log(`Email envoyé à ${message.conversationId.clientId.email}`);
    
    // Mettre à jour le message
    message.statut = 'valide';
    message.dateEnvoi = Date.now();
    message.justification = justification;
    message.modifiePar = 'Administrateur';
    
    await message.save();
    
    res.json(message);
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
});

// PATCH /api/messages/:id/update - Modifier et valider un message
router.patch('/:id/update', async (req, res) => {
  try {
    const { corps, sujet, justification } = req.body;
    
    const message = await Message.findById(req.params.id)
      .populate({
        path: 'conversationId',
        populate: {
          path: 'clientId',
          select: 'nom email telephone'
        }
      });
    
    if (!message) {
      return res.status(404).json({ message: 'Message non trouvé' });
    }

    // Envoyer l'email (simulation)
    console.log(`Email modifié envoyé à ${message.conversationId.clientId.email}`);
    
    // Mettre à jour le message
    message.corps = corps;
    message.sujet = sujet;
    message.statut = 'valide';
    message.dateEnvoi = Date.now();
    message.justification = justification;
    message.modifiePar = 'Administrateur';
    message.dateModification = Date.now();
    
    await message.save();
    
    res.json(message);
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
});

// PATCH /api/messages/:id/reject - Rejeter un message
router.patch('/:id/reject', async (req, res) => {
  try {
    const { justification } = req.body;
    
    const message = await Message.findByIdAndUpdate(
      req.params.id,
      {
        statut: 'rejete',
        justification,
        modifiePar: 'Administrateur',
        dateModification: Date.now()
      },
      { new: true, runValidators: true }
    ).populate({
      path: 'conversationId',
      populate: {
        path: 'clientId',
        select: 'nom email telephone'
      }
    });
    
    if (!message) {
      return res.status(404).json({ message: 'Message non trouvé' });
    }
    
    res.json(message);
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
});

module.exports = router;