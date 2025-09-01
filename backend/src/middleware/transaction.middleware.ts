import { Request, Response, NextFunction } from 'express';
import mongoose from 'mongoose';

/**
 * Middleware pour gérer les transactions MongoDB
 * Crée une session transactionnelle pour les opérations multiples
 */
export const transactionMiddleware = async (
  req: Request, 
  res: Response, 
  next: NextFunction
) => {
  // Créer une nouvelle session MongoDB
  const session = await mongoose.startSession();
  session.startTransaction();
  
  try {
    // Ajouter la session à la requête pour les contrôleurs
    req.transactionSession = session;
    
    // Gestion de la fin de la requête
    res.on('finish', async () => {
      if (res.statusCode >= 200 && res.statusCode < 300) {
        // Commit la transaction si succès
        await session.commitTransaction();
      } else {
        // Annule la transaction en cas d'erreur
        await session.abortTransaction();
      }
      session.endSession();
    });
    
    next();
  } catch (error) {
    // En cas d'erreur pendant le démarrage de la session
    await session.abortTransaction();
    session.endSession();
    next(error);
  }
};

/**
 * Interface étendue pour la requête Express
 */
declare global {
  namespace Express {
    interface Request {
      transactionSession?: mongoose.ClientSession;
    }
  }
}