require('dotenv').config();
const mongoose = require('mongoose');
const Client = require('../models/Client');
const Conversation = require('../models/Conversation');
const Message = require('../models/Message');

const initDatabase = async () => {
  try {
    // Connexion à MongoDB
    await mongoose.connect(process.env.MONGODB_URI);
    console.log('✅ Connecté à MongoDB');

    // Nettoyer la base de données (optionnel)
    console.log('🧹 Nettoyage de la base de données...');
    await Client.deleteMany({});
    await Conversation.deleteMany({});
    await Message.deleteMany({});

    // Créer des clients de test
    console.log('👥 Création des clients...');
    const clients = await Client.insertMany([
      {
        nom: 'Sarra Mabrouk',
        email: 'sarra.mabrouk@gmail.com',
        telephone: '+216 22 345 678',
        statut: 'actif'
      },
      {
        nom: 'Karim Sassi',
        email: 'karim.sassi@gmail.com',
        telephone: '+216 98 123 456',
        statut: 'actif'
      },
      {
        nom: 'Ahmed Ben Ali',
        email: 'ahmed.benali@email.com',
        telephone: '+216 20 123 456',
        statut: 'actif'
      }
    ]);

    // Créer des conversations
    console.log('💬 Création des conversations...');
    const conversations = await Conversation.insertMany([
      {
        clientId: clients[0]._id,
        sujet: 'Résiliation de contrat',
        statut: 'en_attente',
        dernierContact: new Date('2024-01-15T16:20:00'),
        nombreMessages: 2
      },
      {
        clientId: clients[1]._id,
        sujet: 'Demande d\'information',
        statut: 'ouverte',
        dernierContact: new Date('2024-01-15T15:45:00'),
        nombreMessages: 1
      }
    ]);

    // Créer des messages
    console.log('✉️ Création des messages...');
    await Message.insertMany([
      {
        conversationId: conversations[0]._id,
        expediteur: 'client',
        type: 'email',
        sujet: 'Résiliation de contrat',
        corps: 'Est-ce que je peux résilier mon contrat avant échéance ?',
        statut: 'envoye',
        dateEnvoi: new Date('2024-01-15T16:18:00')
      },
      {
        conversationId: conversations[0]._id,
        expediteur: 'agent',
        type: 'email',
        sujet: 'Réponse: Résiliation de contrat',
        corps: 'Oui, vous pouvez résilier votre contrat à tout moment en respectant un préavis de 30 jours. Des frais de résiliation anticipée de 50 DT peuvent s\'appliquer selon les conditions générales de votre contrat.',
        statut: 'en_attente',
        createdAt: new Date('2024-01-15T16:18:00')
      }
    ]);

    console.log('✅ Base de données initialisée avec succès!');
    console.log(`📊 ${clients.length} clients créés`);
    console.log(`📋 ${conversations.length} conversations créées`);
    
    // Afficher les données créées
    const messagesCount = await Message.countDocuments();
    console.log(`✉️ ${messagesCount} messages créés`);
    
    process.exit(0);
  } catch (error) {
    console.error('❌ Erreur lors de l\'initialisation:', error);
    process.exit(1);
  }
};

// Exécuter le script seulement si appelé directement
if (require.main === module) {
  initDatabase();
}

module.exports = initDatabase;