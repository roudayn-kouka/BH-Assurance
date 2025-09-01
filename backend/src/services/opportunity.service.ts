import { Types } from 'mongoose';
import Client from '../models/client.model';
import Message from '../models/message.model';
import Conversation from '../models/conversation.model';

// Calcul du score d'opportunité selon les critères métier
export const computeOpportunityScore = async (clientId: Types.ObjectId | string) => {
  try {
    const client = await Client.findById(clientId);
    if (!client) return;
    
    // 1. Calcul de la récence (0-40 points)
    const recencyScore = calculateRecencyScore(client.last_contact_at);
    
    // 2. Calcul de l'engagement (0-30 points)
    const engagementScore = await calculateEngagementScore(clientId);
    
    // 3. Calcul de la proximité de l'échéance du contrat (0-20 points)
    const expiryScore = calculateExpiryScore(client.contracts);
    
    // 4. Calcul du segment/qualification (0-10 points)
    const segmentScore = calculateSegmentScore(client);
    
    // Calcul du score total
    const totalScore = Math.min(100, Math.round(
      recencyScore + engagementScore + expiryScore + segmentScore
    ));
    
    // Mise à jour du client
    await Client.findByIdAndUpdate(clientId, {
      opportunity_score: totalScore
    });
    
    return totalScore;
  } catch (error) {
    console.error('Erreur lors du calcul du score d\'opportunité:', error);
  }
};

// Calcul de la récence (dernier contact)
const calculateRecencyScore = (lastContact?: Date | null): number => {
  if (!lastContact) return 0;
  
  const daysSinceLastContact = Math.floor(
    (Date.now() - new Date(lastContact).getTime()) / (1000 * 60 * 60 * 24)
  );
  
  // 40 points si contact aujourd'hui, 0 points après 30 jours
  return Math.max(0, 40 - (daysSinceLastContact * (40 / 30)));
};

// Calcul de l'engagement (nombre de messages)
const calculateEngagementScore = async (clientId: Types.ObjectId | string): Promise<number> => {
  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
  
  // Compter les messages des 30 derniers jours
  const messageCount = await Message.countDocuments({
    'conversation_id.client_id': clientId,
    created_at: { $gte: thirtyDaysAgo }
  });
  
  // 30 points maximum (1 point par message jusqu'à 30)
  return Math.min(30, messageCount);
};

// Calcul de la proximité de l'échéance du contrat
const calculateExpiryScore = (contracts: any[]): number => {
  if (!contracts || contracts.length === 0) return 0;
  
  // Trouver le contrat le plus proche de l'échéance
  const activeContracts = contracts.filter(c => 
    c.status === 'active' && c.end_at
  );
  
  if (activeContracts.length === 0) return 0;
  
  // Trouver le contrat avec la date de fin la plus proche
  const closestExpiry = activeContracts
    .map(c => new Date(c.end_at).getTime() - Date.now())
    .reduce((min, current) => Math.min(min, current), Infinity);
  
  // Convertir en jours
  const daysToExpiry = Math.floor(closestExpiry / (1000 * 60 * 60 * 24));
  
  // 20 points si échéance dans moins de 30 jours, 0 points après 60 jours
  return Math.max(0, 20 - (Math.max(0, daysToExpiry) * (20 / 60)));
};

// Calcul du segment/qualification
const calculateSegmentScore = (client: any): number => {
  // 10 points pour les clients actifs avec contrats
  if (client.contracts && client.contracts.some(c => c.status === 'active')) {
    return 10;
  }
  
  // 5 points pour les prospects
  return 5;
};