import rateLimit from 'express-rate-limit';

/**
 * Limiteur de débit global pour les routes API
 * 100 requêtes par 15 minutes par IP
 */
export const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // Limite chaque IP à 100 requêtes par fenêtre
  message: {
    error: 'Trop de requêtes envoyées depuis cette IP, veuillez réessayer plus tard.',
    code: 429,
  },
  standardHeaders: true, // Retourne les en-têtes `RateLimit-*`
  legacyHeaders: false, // Désactive `X-RateLimit-*`
  skipSuccessfulRequests: false, // Compte aussi les requêtes réussies
  handler: (req, res, /* next */) => {
    res.status(429).json({
      error: 'Limite de requêtes dépassée. Veuillez réessayer plus tard.',
      code: 429,
      retryAfter: res.get('Retry-After'), // Temps en secondes
    });
  },
});

/**
 * Limiteur de débit strict pour les routes d'authentification
 * 5 tentatives de login par 15 minutes par IP
 */
export const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 5, // Limite à 5 tentatives
  message: {
    error: 'Trop de tentatives de connexion. Compte temporairement verrouillé.',
    code: 429,
  },
  standardHeaders: true,
  legacyHeaders: false,
  skipSuccessfulRequests: false,
  handler: (req, res, /* next */) => {
    res.status(429).json({
      error: 'Trop de tentatives de connexion. Veuillez réessayer dans 15 minutes.',
      code: 429,
      retryAfter: res.get('Retry-After'),
    });
  },
});