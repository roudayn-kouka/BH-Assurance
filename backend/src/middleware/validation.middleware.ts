import { Request, Response, NextFunction } from 'express';
import { body, param, query, validationResult } from 'express-validator';

/**
 * Middleware de validation pour la création d'un utilisateur
 */
export const validateUser = [
  body('email')
    .isEmail().withMessage('Email invalide')
    .normalizeEmail(),
  body('password')
    .isLength({ min: 6 }).withMessage('Le mot de passe doit contenir au moins 6 caractères'),
  body('role')
    .isIn(['admin', 'validator', 'viewer']).withMessage('Rôle invalide'),
  (req: Request, res: Response, next: NextFunction) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ 
        errors: errors.array() 
      });
    }
    next();
  }
];

/**
 * Middleware de validation pour la création d'un client
 */
export const validateClient = [
  body('email')
    .optional()
    .isEmail().withMessage('Email invalide')
    .normalizeEmail(),
  body('phone')
    .optional()
    .isMobilePhone('any').withMessage('Numéro de téléphone invalide'),
  body('age')
    .optional()
    .isInt({ min: 18, max: 100 }).withMessage('Âge invalide'),
  body('contracts')
    .optional()
    .isArray().withMessage('Les contrats doivent être un tableau'),
  body('contracts.*.premium')
    .optional()
    .isFloat({ min: 0 }).withMessage('Prime invalide'),
  (req: Request, res: Response, next: NextFunction) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ 
        errors: errors.array() 
      });
    }
    next();
  }
];

/**
 * Middleware de validation pour la création d'un message
 */
export const validateMessage = [
  body('conversation_id')
    .exists().withMessage('ID de conversation requis')
    .isMongoId().withMessage('ID de conversation invalide'),
  body('sender')
    .exists().withMessage('Expéditeur requis')
    .isIn(['client', 'ai', 'agent']).withMessage('Expéditeur invalide'),
  body('direction')
    .exists().withMessage('Direction requise')
    .isIn(['inbox', 'sent']).withMessage('Direction invalide'),
  body('body')
    .exists().withMessage('Corps du message requis')
    .isString().withMessage('Corps du message invalide')
    .trim()
    .isLength({ min: 1 }).withMessage('Le message ne peut pas être vide'),
  body('status')
    .optional()
    .isIn(['pending', 'validated', 'rejected']).withMessage('Statut de message invalide'),
  (req: Request, res: Response, next: NextFunction) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ 
        errors: errors.array() 
      });
    }
    next();
  }
];

/**
 * Middleware de validation pour la validation d'un message
 */
export const validateMessageValidation = [
  param('id')
    .exists().withMessage('ID de message requis')
    .isMongoId().withMessage('ID de message invalide'),
  body('action')
    .exists().withMessage('Action requise')
    .isIn(['validate', 'reject']).withMessage('Action invalide'),
  body('edited_body')
    .optional()
    .isString().withMessage('Contenu modifié invalide'),
  body('conversation_status')
    .optional()
    .isIn([
      'nouvelle_opportunite', 'renouvellement', 'upsell_cross_sell',
      'resiliation', 'reclamation', 'support_information',
      'prospect_froid', 'perte_client'
    ]).withMessage('Statut de conversation invalide'),
  body('is_completed')
    .optional()
    .isBoolean().withMessage('is_completed doit être un booléen'),
  (req: Request, res: Response, next: NextFunction) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({ 
        errors: errors.array() 
      });
    }
    next();
  }
];