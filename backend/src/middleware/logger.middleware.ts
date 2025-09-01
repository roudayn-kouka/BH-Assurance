// src/middleware/logger.middleware.ts
import { Request, Response, NextFunction } from 'express';
import morgan from 'morgan';
import fs from 'fs';
import path from 'path';

// ✅ Créer le répertoire de logs s'il n'existe pas
const logDirectory = path.join(__dirname, '../../logs'); // Ajusté pour src/ → logs/
if (!fs.existsSync(logDirectory)) {
  fs.mkdirSync(logDirectory, { recursive: true });
}

// ✅ Créer un stream pour écrire les logs dans un fichier
const accessLogStream = fs.createWriteStream(
  path.join(logDirectory, 'access.log'),
  { flags: 'a' }
);

/**
 * Middleware de logging personnalisé
 * Enregistre les requêtes HTTP dans un fichier
 */
export const requestLogger = morgan(':remote-addr - :method :url :status :response-time ms', {
  stream: accessLogStream
});

/**
 * Middleware de logging détaillé pour le développement
 * ✅ Sécurise l'accès à process.env et req.body
 */
export const detailedLogger = (req: Request, res: Response, next: NextFunction) => {
  const start = Date.now();

  console.log(`\n[${new Date().toISOString()}] Nouvelle requête`);
  console.log(`Méthode: ${req.method}`);
  console.log(`URL: ${req.url}`);
  console.log(`IP: ${req.ip}`);

  // ✅ Sécuriser l'accès à req.body
  if (req.body && typeof req.body === 'object' && Object.keys(req.body).length > 0) {
    console.log('Body:', JSON.stringify(req.body, null, 2));
  }

  // ✅ Sécuriser l'accès à process.env (évite "Cannot convert undefined or null to object")
  if (process.env && typeof process.env === 'object') {
    const loadedKeys = ['NODE_ENV', 'PORT', 'FRONTEND_URL', 'APP_URL']
      .filter(key => process.env[key] !== undefined)
      .map(key => `${key}=${!!process.env[key]}`);
    console.log('Env (keys loaded):', loadedKeys);
  } else {
    console.log('⚠️ process.env non disponible');
  }

  // ✅ Sécuriser l'accès à req.user
  if (req.user) {
    console.log(`Utilisateur authentifié: ${req.user.email} (Rôle: ${req.user.role})`);
  }

  res.on('finish', () => {
    const duration = Date.now() - start;
    console.log(`Réponse: ${res.statusCode} - ${duration}ms`);
  });

  next();
};

/**
 * Middleware de logging pour les erreurs
 */
export const errorLogger = (err: Error, req: Request, res: Response, next: NextFunction) => {
  console.error(`\n[${new Date().toISOString()}] ERREUR INTERCEPTÉE`);
  console.error(`Méthode: ${req.method}`);
  console.error(`URL: ${req.url}`);
  console.error(`IP: ${req.ip}`);
  console.error(`Erreur: ${err.message}`);
  if (err.stack) console.error(`Stack: ${err.stack}`);

  // ✅ Sécuriser l'accès à req.user
  if (req.user) {
    console.error(`Utilisateur: ${req.user.email} (ID: ${req.user._id})`);
  }

  next(err);
};