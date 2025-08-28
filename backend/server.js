// Server.js ultra simplifié sans dépendances problématiques
const http = require('http');

const PORT = process.env.PORT || 5000;

// Données mock pour l'application
const mockData = {
  clients: [
    {
      id: '1',
      nom: 'Sarra Mabrouk',
      email: 'sarra.mabrouk@gmail.com',
      telephone: '+216 22 345 678',
      statut: 'actif'
    },
    {
      id: '2',
      nom: 'Karim Sassi', 
      email: 'karim.sassi@gmail.com',
      telephone: '+216 98 123 456',
      statut: 'actif'
    }
  ],
  messagesPending: [
    {
      id: '1',
      client: 'Sarra Mabrouk',
      question: 'Est-ce que je peux résilier mon contrat avant échéance ?',
      response: 'Oui, vous pouvez résilier votre contrat à tout moment en respectant un préavis de 30 jours. Des frais de résiliation anticipée de 50 DT peuvent s\'appliquer selon les conditions générales de votre contrat.',
      status: 'en_attente'
    }
  ]
};

// Création du serveur HTTP simple
const server = http.createServer((req, res) => {
  // Configuration des headers CORS
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PATCH, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
  
  // Gestion des requêtes OPTIONS pour CORS
  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }
  
  // Routes de l'API
  if (req.method === 'GET') {
    if (req.url === '/') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ 
        message: 'API BH Assurance Dashboard',
        status: 'Connecté',
        version: '1.0.0'
      }));
    }
    else if (req.url === '/api/health') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        status: 'OK',
        timestamp: new Date().toISOString(),
        port: PORT
      }));
    }
    else if (req.url === '/api/clients') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(mockData.clients));
    }
    else if (req.url === '/api/messages/pending') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(mockData.messagesPending));
    }
    else if (req.url === '/api/stats') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        totalConversations: 156,
        pendingValidation: 23,
        satisfactionRate: 98,
        activeClients: 45
      }));
    }
    else {
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ message: 'Route non trouvée' }));
    }
  }
  else if (req.method === 'PATCH' && req.url.startsWith('/api/messages/')) {
    // Simulation de validation de message
    const parts = req.url.split('/');
    const messageId = parts[3];
    
    let body = '';
    req.on('data', chunk => {
      body += chunk.toString();
    });
    
    req.on('end', () => {
      let justification = 'Validé par administrateur';
      try {
        const data = JSON.parse(body);
        if (data.justification) {
          justification = data.justification;
        }
      } catch (e) {
        // Utiliser la valeur par défaut si JSON invalide
      }
      
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        success: true,
        message: `Message ${messageId} validé avec succès`,
        data: {
          id: messageId,
          status: 'valide',
          dateEnvoi: new Date().toISOString(),
          justification: justification
        }
      }));
    });
  }
  else {
    res.writeHead(404, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ message: 'Méthode non autorisée' }));
  }
});

// Démarrage du serveur
server.listen(PORT, () => {
  console.log(`🚀 Serveur BH Assurance démarré sur le port ${PORT}`);
  console.log(`📍 URL: http://localhost:${PORT}`);
  console.log(`📊 Health check: http://localhost:${PORT}/api/health`);
  console.log(`👥 Clients: http://localhost:${PORT}/api/clients`);
  console.log(`⏳ Messages en attente: http://localhost:${PORT}/api/messages/pending`);
  console.log(`📈 Statistiques: http://localhost:${PORT}/api/stats`);
  console.log('');
  console.log('✅ Serveur fonctionnel sans dépendances externes problématiques');
});

// Gestion propre de l'arrêt
process.on('SIGINT', () => {
  console.log('\n🛑 Arrêt du serveur...');
  process.exit(0);
});