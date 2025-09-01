import { Request, Response } from 'express';
import Client from '../models/client.model';

export const getAllClients = async (req: Request, res: Response) => {
  try {
    const { search, page = 1, limit = 10 } = req.query;
    
    // Construction de la requête de recherche
    const query: any = {};
    if (search) {
      query.$or = [
        { email: { $regex: search, $options: 'i' } },
        { first_name: { $regex: search, $options: 'i' } },
        { last_name: { $regex: search, $options: 'i' } },
        { phone: { $regex: search, $options: 'i' } }
      ];
    }

    // Pagination
    const skip = (Number(page) - 1) * Number(limit);
    
    const clients = await Client.find(query)
      .sort({ last_contact_at: -1 })
      .skip(skip)
      .limit(Number(limit));
    
    const total = await Client.countDocuments(query);
    
    res.json({
      clients,
      pagination: {
        total,
        page: Number(page),
        pages: Math.ceil(total / Number(limit))
      }
    });
  } catch (error) {
    console.error('Erreur lors de la récupération des clients:', error);
    res.status(500).json({ error: 'Erreur serveur interne' });
  }
};

export const getClientById = async (req: Request, res: Response) => {
  try {
    const client = await Client.findById(req.params.id);
    if (!client) {
      return res.status(404).json({ error: 'Client non trouvé' });
    }
    res.json(client);
  } catch (error) {
    console.error('Erreur lors de la récupération du client:', error);
    res.status(500).json({ error: 'Erreur serveur interne' });
  }
};

export const createClient = async (req: Request, res: Response) => {
  try {
    const client = new Client(req.body);
    await client.save();
    res.status(201).json(client);
  } catch (error: any) {
    if (error.code === 11000) {
      return res.status(400).json({ error: 'Email déjà utilisé' });
    }
    res.status(500).json({ error: 'Erreur serveur interne' });
  }
};

export const updateClient = async (req: Request, res: Response) => {
  try {
    const client = await Client.findByIdAndUpdate(
      req.params.id,
      req.body,
      { new: true, runValidators: true }
    );
    
    if (!client) {
      return res.status(404).json({ error: 'Client non trouvé' });
    }
    
    res.json(client);
  } catch (error: any) {
    if (error.code === 11000) {
      return res.status(400).json({ error: 'Email déjà utilisé' });
    }
    res.status(500).json({ error: 'Erreur serveur interne' });
  }
};

export const getClientProfile = async (req: Request, res: Response) => {
  try {
    const client = await Client.findById(req.params.id);
    if (!client) {
      return res.status(404).json({ error: 'Client non trouvé' });
    }
    
    // Calcul du score d'opportunité (à implémenter selon vos critères métier)
    const opportunityScore = 75; // Remplacer par votre logique
    
    // Statistiques supplémentaires
    const stats = {
      total_conversations: 5,
      avg_response_time: 2.5,
      last_conversation_date: new Date()
    };
    
    res.json({
      ...client.toObject(),
      opportunityScore,
      stats
    });
  } catch (error) {
    console.error('Erreur lors de la récupération du profil:', error);
    res.status(500).json({ error: 'Erreur serveur interne' });
  }
};