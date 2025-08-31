import { Request, Response, NextFunction } from 'express';
import { ValidationError } from 'express-validation';
import mongoose from 'mongoose';

/**
 * Middleware de gestion des erreurs
 * Gère les différents types d'erreurs et renvoie une réponse appropriée
 */
export const errorHandler = (
  err: Error | ValidationError, 
  req: Request, 
  res: Response, 
  next: NextFunction
) => {
  console.error('Erreur interceptée:', err);
  
  // Erreurs de validation express-validation
  if (err instanceof ValidationError) {
    return res.status(err.statusCode).json({
      error: 'Validation failed',
      details: err.details
    });
  }
  
  // Erreurs MongoDB (ex: validation, clé unique)
  if (err instanceof mongoose.Error.ValidationError) {
    const errors = Object.values(err.errors).map(err => err.message);
    return res.status(400).json({ 
      error: 'Validation Error', 
      details: errors 
    });
  }
  
  // Erreur de clé unique MongoDB
  if (err instanceof mongoose.Error && err.message.includes('E11000')) {
    return res.status(400).json({ 
      error: 'Données en conflit', 
      details: 'Cette ressource existe déjà.' 
    });
  }
  
  // Erreur de document non trouvé
  if (err.message === 'Not Found') {
    return res.status(404).json({ 
      error: 'Ressource non trouvée' 
    });
  }
  
  // Erreurs connues avec message spécifique
  if (err.message && ['Invalid credentials', 'Token expired', 'Access denied'].includes(err.message)) {
    return res.status(401).json({ 
      error: err.message 
    });
  }
  
  // Erreur par défaut
  res.status(500).json({ 
    error: 'Erreur serveur interne',
    message: process.env.NODE_ENV === 'development' ? err.message : undefined
  });
};

/**
 * Middleware pour gérer les routes non trouvées
 */
export const notFoundHandler = (req: Request, res: Response, next: NextFunction) => {
  res.status(404).json({ 
    error: 'Route non trouvée',
    path: req.path 
  });
};