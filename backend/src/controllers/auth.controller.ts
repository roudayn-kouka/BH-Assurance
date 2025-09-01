import { Request, Response } from 'express';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import User from '../models/user.model';

// Durée du token JWT (24h)
const JWT_EXPIRATION = 24 * 60 * 60;

export const login = async (req: Request, res: Response) => {
  try {
    const { email, password } = req.body;
    
    // Validation des champs
    if (!email || !password) {
      return res.status(400).json({ error: 'Email et mot de passe requis' });
    }

    // Recherche de l'utilisateur
    const user = await User.findOne({ email });
    if (!user) {
      return res.status(401).json({ error: 'Identifiants incorrects' });
    }

    // Vérification du mot de passe
    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) {
      return res.status(401).json({ error: 'Identifiants incorrects' });
    }

    // Génération du token JWT
    const token = jwt.sign(
      { id: user._id, role: user.role },
      process.env.JWT_SECRET!,
      { expiresIn: JWT_EXPIRATION }
    );

    // Réponse avec token et informations utilisateur
    res.json({
      token,
      user: {
        id: user._id,
        email: user.email,
        role: user.role
      }
    });
  } catch (error) {
    console.error('Erreur de login:', error);
    res.status(500).json({ error: 'Erreur serveur interne' });
  }
};

// Enregistrement d'un nouvel utilisateur (pour admin)
// Rôles autorisés
const VALID_ROLES = ['admin', 'validator', 'user'] as const;
type Role = typeof VALID_ROLES[number];

export const register = async (req: Request, res: Response) => {
  try {
    const { email, password, role } = req.body;

    if (!email || !password || !role) {
      return res.status(400).json({ error: 'Tous les champs sont requis' });
    }

    // ✅ Vérifiez que le rôle est valide
    if (!VALID_ROLES.includes(role)) {
      return res.status(400).json({ error: 'Rôle invalide' });
    }

    const existingUser = await User.findOne({ email });
    if (existingUser) {
      return res.status(400).json({ error: 'Email déjà utilisé' });
    }

    const salt = await bcrypt.genSalt(10);
    const hashedPassword = await bcrypt.hash(password, salt);

    const user = new User({ email, password: hashedPassword, role });
    await user.save();

    const token = jwt.sign(
      { id: user._id, role: user.role },
      process.env.JWT_SECRET!,
      { expiresIn: JWT_EXPIRATION }
    );

    res.status(201).json({
      token,
      user: {
        id: user._id,
        email: user.email,
        role: user.role
      }
    });
  } catch (error) {
    console.error('Erreur d\'enregistrement:', error);
    res.status(500).json({ error: 'Erreur serveur interne' });
  }
};