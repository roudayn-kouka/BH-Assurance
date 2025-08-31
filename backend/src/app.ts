// 🔥 1. Charger dotenv IMMÉDIATEMENT
import 'dotenv/config';

// ✅ 2. Maintenant, les imports
import express, { Request, Response, NextFunction } from 'express';
import mongoose from 'mongoose';
import cors from 'cors';
import morgan from 'morgan';
import path from 'path';
import fs from 'fs';

// ✅ Routes et middlewares
import routes from './routes';
import { securityMiddleware } from './middleware/security.middleware';
import { errorHandler, notFoundHandler } from './middleware/error.handler';
import { configMiddleware } from './middleware/config.middleware';
import { requestLogger, detailedLogger } from './middleware/logger.middleware';
import { apiLimiter, authLimiter } from './middleware/rate-limit.middleware';
import { transactionMiddleware } from './middleware/transaction.middleware';

// ✅ Créer l'application Express
const app = express();

// ✅ Configuration du port
const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 3001;

// ✅ Créer le répertoire de logs (chemin corrigé pour fonctionner en dev et prod)
const logDirectory = path.join(__dirname, '../logs'); // '../logs' pour src/ → logs/
if (!fs.existsSync(logDirectory)) {
  fs.mkdirSync(logDirectory, { recursive: true });
}
const corsOptions = {
  origin: [
    'http://localhost:8080', // Frontend React
    'http://localhost:3000', // Autre port possible
    'https://votre-frontend.com' // En production
  ],
  credentials: true, // Autorise les cookies et tokens
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
};


// ✅ Middleware de base
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// ✅ Middleware de sécurité
app.use(securityMiddleware);

// ✅ Middleware CORS sécurisé
app.use((req: Request, res: Response, next: NextFunction) => {
  const allowedOrigins = [
    'http://localhost:3000',
    process.env.FRONTEND_URL
  ].filter((origin): origin is string => Boolean(origin));

  const origin = req.headers.origin;

  if (origin && allowedOrigins.includes(origin)) {
    res.header('Access-Control-Allow-Origin', origin);
  }

  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, PATCH, DELETE, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  res.header('Access-Control-Allow-Credentials', 'true');

  if (req.method === 'OPTIONS') {
    return res.sendStatus(200);
  }

  next();
});

// ✅ Middleware de logging
if (process.env.NODE_ENV === 'development') {
  app.use(morgan('dev'));
  // ✅ Sécuriser detailedLogger contre process.env undefined
  app.use((req, res, next) => {
    // Forcer un accès initial à process.env pour le charger
    if (process.env) {
      detailedLogger(req, res, next);
    } else {
      console.warn('process.env est undefined, skipped detailedLogger');
      next();
    }
  });
} else {
  const accessLogStream = fs.createWriteStream(
    path.join(logDirectory, 'access.log'),
    { flags: 'a' }
  );
  app.use(morgan('combined', { stream: accessLogStream }));
}

// ✅ Middleware de configuration globale
app.use(configMiddleware);

// ✅ Routes publiques avec limitation de débit
app.use('/api/auth/login', authLimiter);
app.use('/api/auth/register', authLimiter);

// ✅ Routes API avec limitation de débit
app.use('/api', apiLimiter, routes);

// ✅ Gestion des erreurs
app.use(errorHandler);
app.use(notFoundHandler);

// ✅ Connexion à MongoDB
const connectDB = async () => {
  try {
    if (!process.env.MONGODB_URI) {
      throw new Error('❌ MONGODB_URI non définie dans .env');
    }

    await mongoose.connect(process.env.MONGODB_URI);
    console.log('✅ Connecté à MongoDB avec succès');

    app.listen(PORT, () => {
      console.log(`\n🚀 Serveur démarré sur http://localhost:${PORT}`);
      console.log('----------------------------------------');
      console.log('Endpoints disponibles :');
      console.log('----------------------------------------');
      console.log('🔐 Authentification:');
      console.log('  POST   /api/auth/login');
      console.log('  POST   /api/auth/register');
      console.log('\n👥 Clients:');
      console.log('  GET    /api/clients');
      console.log('  GET    /api/clients/:id');
      console.log('  GET    /api/clients/:id/profile');
      console.log('  POST   /api/clients');
      console.log('  PUT    /api/clients/:id');
      console.log('\n💬 Conversations:');
      console.log('  GET    /api/conversations');
      console.log('  GET    /api/conversations/:id');
      console.log('  POST   /api/conversations');
      console.log('  PATCH  /api/conversations/:id');
      console.log('\n✉️ Messages:');
      console.log('  GET    /api/conversations/:conversationId/messages');
      console.log('  POST   /api/messages');
      console.log('  PATCH  /api/messages/:id/validate');
      console.log('\n✅ Validation:');
      console.log('  GET    /api/validation/queue');
      console.log('\n📊 Analytics:');
      console.log('  GET    /api/analytics/summary');
      console.log('  GET    /api/analytics/time-series');
      console.log('\n✅ Health Check:');
      console.log('  GET    /api/health');
      console.log('----------------------------------------');
      console.log(`Environnement : ${process.env.NODE_ENV || 'development'}`);
      console.log('----------------------------------------\n');
    });
  } catch (error) {
    console.error('❌ Échec de la connexion à MongoDB:', error);
    setTimeout(connectDB, 5000);
  }
};

// ✅ Gestion des erreurs système
process.on('unhandledRejection', (error: Error) => {
  console.error('Unhandled Promise Rejection:', error.message);
  mongoose.disconnect();
  process.exit(1);
});

process.on('uncaughtException', (error: Error) => {
  console.error('Uncaught Exception:', error.message);
  mongoose.disconnect();
  process.exit(1);
});

// ✅ Démarrer la connexion
connectDB();

export default app;