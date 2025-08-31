import { Request, Response, NextFunction } from 'express';

/**
 * Middleware pour ajouter des informations de configuration à la requête
 */
export const configMiddleware = (req: Request, res: Response, next: NextFunction) => {
  // Ajouter des informations de configuration à la requête
  req.config = {
    appVersion: process.env.npm_package_version || '1.0.0',
    env: process.env.NODE_ENV || 'development',
    features: {
      emailNotifications: !!process.env.SMTP_USER,
      analytics: true,
      validationQueue: true
    }
  };
  
  next();
};

/**
 * Interface étendue pour la requête Express
 */
declare global {
  namespace Express {
    interface Request {
      config?: {
        appVersion: string;
        env: string;
        features: {
          emailNotifications: boolean;
          analytics: boolean;
          validationQueue: boolean;
        };
      };
      user?: any; // À remplacer par un type utilisateur spécifique
    }
  }
}