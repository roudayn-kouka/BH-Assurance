const express = require('express');
const router = express.Router();
const Conversation = require('../models/Conversation');
const Message = require('../models/Messages');
const Client = require('../models/Client');

// GET /api/stats - Récupérer les statistiques globales
router.get('/', async (req, res) => {
  try {
    // Statistiques des conversations
    const totalConversations = await Conversation.countDocuments();
    const openConversations = await Conversation.countDocuments({ statut: 'ouverte' });
    const pendingConversations = await Conversation.countDocuments({ statut: 'en_attente' });
    
    // Statistiques des messages
    const totalMessages = await Message.countDocuments();
    const pendingMessages = await Message.countDocuments({ statut: 'en_attente' });
    
    // Statistiques des clients
    const totalClients = await Client.countDocuments();
    const activeClients = await Client.countDocuments({ statut: 'actif' });
    
    // Taux de satisfaction moyen
    const avgSatisfaction = await Conversation.aggregate([
      {
        $group: {
          _id: null,
          avgSatisfaction: { $avg: '$satisfaction' }
        }
      }
    ]);
    
    // Dernière activité
    const lastActivity = await Conversation.findOne()
      .sort({ dernierContact: -1 })
      .select('dernierContact');
    
    res.json({
      totalConversations,
      openConversations,
      pendingConversations,
      totalMessages,
      pendingMessages,
      totalClients,
      activeClients,
      satisfactionRate: Math.round(avgSatisfaction[0]?.avgSatisfaction || 0),
      recentActivity: lastActivity?.dernierContact || new Date()
    });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
});

module.exports = router;