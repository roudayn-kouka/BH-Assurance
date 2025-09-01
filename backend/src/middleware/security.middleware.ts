import { Request, Response, NextFunction } from 'express';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import slowDown from 'express-slow-down';

/**
 * Middleware de sécurité de base
 * Utilise Helmet pour sécuriser les en-têtes HTTP
 */
export const securityMiddleware = helmet({
  contentSecurityPolicy: false, // À configurer selon vos besoins
  crossOriginEmbedderPolicy: false,
});

/**
 * Middleware de limitation de débit (rate limiting)
 * Limite à 100 requêtes par 15 minutes par IP
 */
export const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // Limite chaque IP à 100 requêtes par fenêtre
  standardHeaders: true, // Retourne les en-têtes RateLimit
  legacyHeaders: false, // Désactive les en-têtes X-RateLimit
  message: 'Trop de requêtes depuis cette IP, veuillez réessayer plus tard.',
});

/**
 * Middleware de limitation de débit pour l'authentification
 * Plus strict pour les endpoints de login
 */
export const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 5, // Limite à 5 tentatives de login par fenêtre
  message: 'Trop de tentatives de connexion. Compte verrouillé pendant 15 minutes.',
});

/**
 * Middleware de ralentissement des requêtes
 * Pour ralentir les attaques par force brute
 */
export const apiSlowDown = slowDown({
  windowMs: 15 * 60 * 1000, // 15 minutes
  delayAfter: 50, // Commence à ralentir après 50 requêtes
  delayMs: (numberOfRequests) => numberOfRequests * 500, // Augmente le délai
});

/**
 * Middleware de validation CORS personnalisé
 * Contrôle strict des origines autorisées
 */
export const corsMiddleware = (req: Request, res: Response, next: NextFunction) => {
  const allowedOrigins = [
    'http://localhost:3000', // Frontend en développement
    'https://votre-frontend.com' // Frontend en production
  ];
  
  const origin = req.headers.origin || '';
  
  if (allowedOrigins.includes(origin)) {
    res.header('Access-Control-Allow-Origin', origin);
  }
  
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.header('Access-Control-Allow-Credentials', 'true');
  
  // Gestion des requêtes préflight
  if (req.method === 'OPTIONS') {
    return res.sendStatus(200);
  }
  
  next();
};