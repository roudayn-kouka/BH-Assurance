import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import User from '../models/user.model';

/**
 * Middleware d'authentification JWT
 * Vérifie la présence et la validité du token JWT dans l'en-tête Authorization
 */
export const authenticate = async (req: Request, res: Response, next: NextFunction) => {
  try {
    // Extraction du token depuis l'en-tête Authorization
    const authHeader = req.header('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ 
        error: 'Accès non autorisé. Token manquant ou invalide.' 
      });
    }

    const token = authHeader.replace('Bearer ', '');
    
    // Décodage et vérification du token
    const decoded = jwt.verify(token, process.env.JWT_SECRET!) as {
      id: string;
      role: string;
      iat: number;
      exp: number;
    };
    
    // Vérification de l'existence de l'utilisateur
    const user = await User.findById(decoded.id).select('-password');
    if (!user) {
      return res.status(401).json({ 
        error: 'Token invalide ou utilisateur non trouvé.' 
      });
    }
    
    // Ajout de l'utilisateur à la requête pour les middlewares/controlleurs suivants
    req.user = user;
    
    next();
  } catch (error) {
    if (error instanceof jwt.TokenExpiredError) {
      return res.status(401).json({ 
        error: 'Session expirée. Veuillez vous reconnecter.' 
      });
    }
    
    if (error instanceof jwt.JsonWebTokenError) {
      return res.status(401).json({ 
        error: 'Token invalide.' 
      });
    }
    
    console.error('Erreur d\'authentification:', error);
    res.status(500).json({ 
      error: 'Erreur serveur lors de l\'authentification.' 
    });
  }
};

/**
 * Middleware d'autorisation par rôle
 * Vérifie si l'utilisateur a au moins l'un des rôles spécifiés
 * 
 * @param allowedRoles - Liste des rôles autorisés pour cette route
 */
export const authorize = (allowedRoles: string[]) => {
  return (req: Request, res: Response, next: NextFunction) => {
    if (!req.user) {
      return res.status(401).json({ 
        error: 'Accès non autorisé. Utilisateur non authentifié.' 
      });
    }
    
    if (!allowedRoles.includes(req.user.role)) {
      return res.status(403).json({ 
        error: `Accès interdit. Rôle requis: ${allowedRoles.join(', ')}.` 
      });
    }
    
    next();
  };
};

/**
 * Middleware combiné pour authentification + autorisation
 * 
 * @param allowedRoles - Liste des rôles autorisés pour cette route
 */
export const authMiddleware = (allowedRoles: string[]) => {
  return [
    authenticate,
    authorize(allowedRoles)
  ];
};