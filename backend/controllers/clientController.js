const Client = require('../models/Client');
const Conversation = require('../models/Conversation');

// Obtenir tous les clients
exports.getClients = async (req, res) => {
  try {
    const page = parseInt(req.query.page) || 1;
    const limit = parseInt(req.query.limit) || 10;
    const skip = (page - 1) * limit;
    
    const clients = await Client.find()
      .sort({ nom: 1 })
      .skip(skip)
      .limit(limit);
    
    const total = await Client.countDocuments();
    
    res.json({
      clients,
      currentPage: page,
      totalPages: Math.ceil(total / limit),
      totalClients: total
    });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
};

// Obtenir un client par ID
exports.getClientById = async (req, res) => {
  try {
    const client = await Client.findById(req.params.id);
    if (!client) {
      return res.status(404).json({ message: 'Client non trouvé' });
    }
    
    // Récupérer les conversations du client
    const conversations = await Conversation.find({ clientId: req.params.id })
      .sort({ dernierContact: -1 });
    
    res.json({ client, conversations });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
};

// Créer un nouveau client
exports.createClient = async (req, res) => {
  try {
    const { nom, email, telephone } = req.body;
    
    // Vérifier si le client existe déjà
    const existingClient = await Client.findOne({ email });
    if (existingClient) {
      return res.status(400).json({ message: 'Un client avec cet email existe déjà' });
    }
    
    const client = new Client({
      nom,
      email,
      telephone
    });
    
    const newClient = await client.save();
    res.status(201).json(newClient);
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
};

// Mettre à jour un client
exports.updateClient = async (req, res) => {
  try {
    const client = await Client.findByIdAndUpdate(
      req.params.id,
      req.body,
      { new: true, runValidators: true }
    );
    
    if (!client) {
      return res.status(404).json({ message: 'Client non trouvé' });
    }
    
    res.json(client);
  } catch (error) {
    res.status(400).json({ message: error.message });
  }
};

// Supprimer un client
exports.deleteClient = async (req, res) => {
  try {
    const client = await Client.findByIdAndDelete(req.params.id);
    
    if (!client) {
      return res.status(404).json({ message: 'Client non trouvé' });
    }
    
    // Supprimer également les conversations associées
    await Conversation.deleteMany({ clientId: req.params.id });
    
    res.json({ message: 'Client supprimé avec succès' });
  } catch (error) {
    res.status(500).json({ message: error.message });
  }
};