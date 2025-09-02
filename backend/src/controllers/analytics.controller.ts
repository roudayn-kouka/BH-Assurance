// src/controllers/analytics.controller.ts

import { Request, Response } from 'express';
import Message from '../models/message.model';
import Conversation from '../models/conversation.model';
import Client from '../models/client.model';

export const getAnalyticsSummary = async (req: Request, res: Response) => {
  try {
    const { from, to } = req.query;
    
    const startDate = from ? new Date(from as string) : new Date(0);
    const endDate = to ? new Date(to as string) : new Date();

    const [
      totalConversations,
      validatedMessages,
      messages,
      conversations
    ] = await Promise.all([
      Conversation.countDocuments({ created_at: { $gte: startDate, $lte: endDate } }),
      Message.countDocuments({ status: 'validated', created_at: { $gte: startDate, $lte: endDate } }),
      Message.find({ created_at: { $gte: startDate, $lte: endDate } }),
      Conversation.find({ created_at: { $gte: startDate, $lte: endDate } })
    ]);

    const messagesModifies = messages.filter(m => m.is_modified).length;

    // Comptage par statut (en anglais)
    const stats = conversations.reduce((acc, conv) => {
      switch (conv.status) {
        case 'new_opportunity': acc.newOpportunities++; break;
        case 'renouvellement': acc.renewals++; break;
        case 'upsell_cross_sell': acc.upsellCrossSell++; break;
        case 'resiliation': acc.resiliations++; break;
        case 'perte_client': acc.perteClients++; break;
        case 'support_information': acc.supportInformation++; break;
        case 'reclamation': acc.reclamations++; break;
        case 'prospect_froid': acc.prospectsFroids++; break;
      }
      return acc;
    }, {
      newOpportunities: 0, renewals: 0, upsellCrossSell: 0,
      resiliations: 0, perteClients: 0, supportInformation: 0,
      reclamations: 0, prospectsFroids: 0
    });

    // Calcul des "obtention clients"
    const obtentionClients = stats.newOpportunities + stats.renewals;

    // Simulation d'évolution mensuelle
    const trends = {
      conversationsEvolution: 12,
      opportunitesEvolution: 8,
      resiliationsEvolution: -5,
      obtentionEvolution: 15
    };

    res.json({
      data: {
        totalConversations,
        messagesModifies,
        obtentionClients,
        ...stats
      },
      trends
    });
  } catch (error) {
    res.status(500).json({ error: 'Erreur serveur' });
  }
};

export const getTimeSeriesAnalytics = async (req: Request, res: Response) => {
  try {
    const { from, to, granularity = 'daily' } = req.query;
    
    const startDate = from ? new Date(from as string) : new Date(0);
    const endDate = to ? new Date(to as string) : new Date();
    
    let dateFormat;
    switch (granularity) {
      case 'daily':
        dateFormat = '%Y-%m-%d';
        break;
      case 'weekly':
        dateFormat = '%Y-%U';
        break;
      case 'monthly':
        dateFormat = '%Y-%m';
        break;
      default:
        dateFormat = '%Y-%m-%d';
    }
    
    const messageTrends = await Message.aggregate([
      { $match: { created_at: { $gte: startDate, $lte: endDate } } },
      {
        $group: {
          _id: {
            $dateToString: { format: dateFormat, date: '$created_at' }
          },
          total: { $sum: 1 },
          validated: { 
            $sum: { $cond: [{ $eq: ['$status', 'validated'] }, 1, 0] } 
          },
          rejected: { 
            $sum: { $cond: [{ $eq: ['$status', 'rejected'] }, 1, 0] } 
          }
        }
      },
      { $sort: { _id: 1 } }
    ]);
    
    const conversationTrends = await Conversation.aggregate([
      { $match: { last_activity_at: { $gte: startDate, $lte: endDate } } },
      {
        $group: {
          _id: {
            $dateToString: { format: dateFormat, date: '$last_activity_at' }
          },
          total: { $sum: 1 },
          completed: { 
            $sum: { $cond: ['$is_completed', 1, 0] } 
          }
        }
      },
      { $sort: { _id: 1 } }
    ]);
    
    res.json({
      message_trends: messageTrends,
      conversation_trends: conversationTrends
    });
  } catch (error) {
    console.error('Erreur lors du calcul des séries temporelles:', error);
    res.status(500).json({ error: 'Erreur serveur interne' });
  }
};