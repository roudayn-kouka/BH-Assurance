const mongoose = require('mongoose');
const dotenv = require('dotenv');
const Client = require('../models/Client');
const Conversation = require('../models/Conversation');
const Message = require('../models/Messages');
const connectDB = require('../config/database');

// Charger les variables d'environnement
dotenv.config();

// Données de test réalistes (basées sur le dataset fourni)
const clientsData = [
  {
    nom: 'Ahmed Kacem',
    email: 'ahmed10+101372@gmail.com',
    telephone: '+216 71 123 456',
    statut: 'actif'
  },
  {
    nom: 'Mohamed Ali',
    email: 'ahmed10+103100@gmail.com',
    telephone: '+216 71 234 567',
    statut: 'actif'
  },
  {
    nom: 'Salma Ben Youssef',
    email: 'ahmed10+103147@gmail.com',
    telephone: '+216 71 345 678',
    statut: 'en_attente'
  }
];

const sujetsConversation = [
  'MULTIRISQUES PROFESSIONNELLES CENTRALISE',
  'MULTIRISQUES PROFESSIONNELLES',
  'AUTOMOBILE',
  'AUTOMOBILE AMICALE',
  'OMNICANAL AUTOMOBILE PACK2',
  'RESPONSABILITE CIVILE',
  'ASSISTANCES EN VOYAGES - PLAN BASIQUE',
  'POLICE AU VOYAGE(CORPS DE PLAISANCE)',
  'TRANSPORT CORPS AVIATION'
];

const messagesTemplates = {
  client: [
    "Pouvez-vous me donner plus de détails sur cette offre de produit ?",
    "Quel est le tarif pour ce conseil (estimation mensuelle / annuelle) ?",
    "Cette garantie couvre-t-elle les dommages lors d'une activité professionnelle ?",
    "Est-ce que la police au voyage serait adaptée pour nos opérations maritimes ?",
    "Je ne suis pas encore décidé, je veux comparer les scores et conditions.",
    "Cela semble bien : quel est le taux de franchise ?",
    "Pouvez-vous m'envoyer le détail de la couverture et le score de recommandation ?",
    "Je préfère ne pas souscrire pour l'instant, merci pour l'info.",
    "Avez-vous une formule qui combine automobile et responsabilité civile ?",
    "Très bien, envoyez-moi le contrat par email pour finaliser."
  ],
  agent: [
    "Bonjour, nous avons une offre adaptée à votre secteur qui obtient un score élevé de recommandation.",
    "Le produit a un fort historique de souscription pour des profils similaires au vôtre.",
    "Cette formule combine assistance et responsabilité civile, utile pour opérations à risques.",
    "Nous pouvons regrouper plusieurs garanties (multirisques + incendie) pour un tarif avantageux.",
    "L'assistance voyage incluse couvre l'équipage et le matériel en mer, selon la formule choisie.",
    "Le score de recommandation pour ce produit est élevé — je peux vous détailler les raisons.",
    "Si vous souscrivez aujourd'hui, nous appliquons un bonus de bienvenue.",
    "Je peux préparer une proposition qui montre le score machine et l'historique des clients similaires.",
    "Souhaitez-vous que je vous envoie la fiche produit et le tableau des garanties par email ?",
    "Je peux lancer la souscription dès réception des pièces — voulez-vous procéder ?"
  ]
};

async function seedDatabase() {
  try {
    console.log('🔄 Connexion à la base de données...');
    await connectDB();

    console.log('🗑️  Suppression des données existantes...');
    await Message.deleteMany({});
    await Conversation.deleteMany({});
    await Client.deleteMany({});

    console.log('👥 Insertion des clients...');
    const clients = await Client.insertMany(clientsData);
    console.log(`✅ ${clients.length} clients créés`);

    console.log('💬 Création des conversations...');
    const conversations = [];

    for (const client of clients) {
      // Chaque client a entre 1 et 3 conversations
      const nbConversations = Math.floor(Math.random() * 3) + 1;

      for (let i = 0; i < nbConversations; i++) {
        const sujet = sujetsConversation[Math.floor(Math.random() * sujetsConversation.length)];
        const statuts = ['ouverte', 'fermee', 'en_attente'];
        const statut = statuts[Math.floor(Math.random() * statuts.length)];
        const satisfaction = statut === 'fermee' ? Math.floor(Math.random() * 41) + 60 : 0; // 60-100 pour les fermées

        const conversation = {
          clientId: client._id,
          sujet: sujet,
          statut: statut,
          dernierContact: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000), // Dans les 30 derniers jours
          satisfaction: satisfaction,
          nombreMessages: 0 // Sera mis à jour après création des messages
        };

        conversations.push(conversation);
      }
    }

    const savedConversations = await Conversation.insertMany(conversations);
    console.log(`✅ ${savedConversations.length} conversations créées`);

    console.log('📧 Création des messages...');
    const messages = [];

    for (const conversation of savedConversations) {
      // Chaque conversation a entre 2 et 8 messages
      const nbMessages = Math.floor(Math.random() * 7) + 2;
      let messageCount = 0;

      for (let i = 0; i < nbMessages; i++) {
        const expediteur = i % 2 === 0 ? 'agent' : 'client'; // Alternance client/agent
        const type = 'email';
        const templates = messagesTemplates[expediteur];
        const corps = templates[Math.floor(Math.random() * templates.length)];

        let statut = 'valide';
        if (expediteur === 'agent' && Math.random() < 0.3) {
          statut = ['en_attente', 'rejete'][Math.floor(Math.random() * 2)];
        }

        const message = {
          conversationId: conversation._id,
          expediteur: expediteur,
          type: type,
          sujet: conversation.sujet,
          corps: corps,
          statut: statut,
          createdAt: new Date(conversation.dernierContact.getTime() + i * 2 * 60 * 60 * 1000), // Messages espacés de 2h
        };

        // Ajouter des champs pour les messages traités
        if (statut !== 'en_attente') {
          message.dateEnvoi = new Date(message.createdAt.getTime() + 30 * 60 * 1000); // 30 min après création
        }

        if (statut === 'rejete') {
          message.justification = 'Message non conforme aux standards de communication';
          message.modifiePar = 'Superviseur';
          message.dateModification = message.dateEnvoi;
        }

        messages.push(message);
        messageCount++;
      }

      // Mettre à jour le nombre de messages dans la conversation
      await Conversation.findByIdAndUpdate(conversation._id, { nombreMessages: messageCount });
    }

    const savedMessages = await Message.insertMany(messages);
    console.log(`✅ ${savedMessages.length} messages créés`);

    console.log('📊 Résumé des données créées :');
    console.log(`   👥 Clients: ${clients.length}`);
    console.log(`   💬 Conversations: ${savedConversations.length}`);
    console.log(`   📧 Messages: ${savedMessages.length}`);

    // Afficher quelques statistiques
    const statsClients = await Client.aggregate([
      { $group: { _id: '$statut', count: { $sum: 1 } } }
    ]);

    const statsConversations = await Conversation.aggregate([
      { $group: { _id: '$statut', count: { $sum: 1 } } }
    ]);

    const statsMessages = await Message.aggregate([
      { $group: { _id: '$statut', count: { $sum: 1 } } }
    ]);

    console.log('\n📈 Statistiques par statut :');
    console.log('Clients:', statsClients);
    console.log('Conversations:', statsConversations);
    console.log('Messages:', statsMessages);

    console.log('\n🎉 Données de test insérées avec succès !');

  } catch (error) {
    console.error('❌ Erreur lors de l\'insertion des données:', error);
  } finally {
    await mongoose.connection.close();
    console.log('🔚 Connexion fermée');
    process.exit(0);
  }
}

// Fonction utilitaire pour générer des dates aléaoires
function randomDate(start, end) {
  return new Date(start.getTime() + Math.random() * (end.getTime() - start.getTime()));
}

// Exécuter le script
if (require.main === module) {
  console.log('🌱 Démarrage du seeding de la base de données...');
  seedDatabase();
}

module.exports = seedDatabase;
