const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');
const connectDB = require('./config/database');

// Charger les variables d'environnement
dotenv.config();

// Importer les routes
const clientRoutes = require('./routes/clients');
const conversationRoutes = require('./routes/conversations');
const messageRoutes = require('./routes/messages');
const statsRoutes = require('./routes/stats');

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors());
app.use(express.json());

// Connexion à MongoDB
connectDB();

// Routes
app.use('/api/clients', clientRoutes);
app.use('/api/conversations', conversationRoutes);
app.use('/api/messages', messageRoutes);
app.use('/api/stats', statsRoutes);

// Route de base
app.get('/', (req, res) => {
  res.json({ 
    message: 'API BH Assurance Dashboard',
    database: 'MongoDB',
    status: 'Connecté'
  });
});

// Route de santé
app.get('/api/health', async (req, res) => {
  try {
    const mongoose = require('mongoose');
    const dbState = mongoose.connection.readyState;
    
    const states = {
      0: 'Déconnecté',
      1: 'Connecté',
      2: 'Connexion en cours',
      3: 'Déconnexion en cours'
    };
    
    res.json({
      database: 'MongoDB',
      status: states[dbState] || 'Inconnu',
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Gestion des erreurs 404
app.use('*', (req, res) => {
  res.status(404).json({ message: 'Route non trouvée' });
});

// Démarrage du serveur
app.listen(PORT, () => {
  console.log(`🚀 Serveur démarré sur le port ${PORT}`);
  console.log(`📍 URL: http://localhost:${PORT}`);
});