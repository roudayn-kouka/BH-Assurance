const express = require('express');
const router = express.Router();
const Conversation = require('../models/Conversation');
const Message = require('../models/Messages');

// GET /api/conversations - Récupérer toutes les conversations
router.get('/', async (req, res) => {
  try {
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 10;
    const skip = (page - 1) * limit;
    const { statut } = req.query;
    
    let filter = {};
    if (statut) filter.statut = statut;
    
    const conversations = await Conversation.find(filter)
      .populate('clientId', 'nom email telephone')
      .sort({ dernierContact: -1 })
      .skip(skip)
      .limit(limit);
    
    const total = await Conversation.countDocuments(filter);
    
    res.json({
      conversations,
      currentPage: page,
      totalPages: Math.ceil(total / limit),
      totalConversations: total
    });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

// GET /api/conversations/stats - Récupérer les statistiques des conversations
router.get('/stats', async (req, res) => {
  try {
    const totalConversations = await Conversation.countDocuments();
    const openConversations = await Conversation.countDocuments({ statut: 'ouverte' });
    const pendingConversations = await Conversation.countDocuments({ statut: 'en_attente' });
    
    const avgSatisfaction = await Conversation.aggregate([
      {
        $group: {
          _id: null,
          avgSatisfaction: { $avg: '$satisfaction' }
        }
      }
    ]);
    
    res.json({
      totalConversations,
      openConversations,
      pendingConversations,
      avgSatisfaction: avgSatisfaction[0]?.avgSatisfaction || 0
    });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

// GET /api/conversations/:id - Récupérer une conversation par ID
router.get('/:id', async (req, res) => {
  try {
    const conversation = await Conversation.findById(req.params.id)
      .populate('clientId', 'nom email telephone');
    
    if (!conversation) {
      return res.status(404).json({ message: 'Conversation non trouvée' });
    }
    
    // Récupérer tous les messages de la conversation
    const messages = await Message.find({ conversationId: req.params.id })
      .sort({ createdAt: 1 });
    
    res.json({ conversation, messages });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

// POST /api/conversations - Créer une nouvelle conversation
router.post('/', async (req, res) => {
  try {
    const { clientId, sujet } = req.body;
    
    const conversation = new Conversation({
      clientId,
      sujet
    });
    
    const newConversation = await conversation.save();
    await newConversation.populate('clientId', 'nom email telephone');
    
    res.status(201).json(newConversation);
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
});

// PUT /api/conversations/:id - Mettre à jour une conversation
router.put('/:id', async (req, res) => {
  try {
    const conversation = await Conversation.findByIdAndUpdate(
      req.params.id,
      req.body,
      { new: true, runValidators: true }
    ).populate('clientId', 'nom email telephone');
    
    if (!conversation) {
      return res.status(404).json({ message: 'Conversation non trouvée' });
    }
    
    res.json(conversation);
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
});

// PATCH /api/conversations/:id/close - Fermer une conversation
router.patch('/:id/close', async (req, res) => {
  try {
    const conversation = await Conversation.findByIdAndUpdate(
      req.params.id,
      { statut: 'fermee' },
      { new: true, runValidators: true }
    ).populate('clientId', 'nom email telephone');
    
    if (!conversation) {
      return res.status(404).json({ message: 'Conversation non trouvée' });
    }
    
    res.json(conversation);
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
});

module.exports = router;