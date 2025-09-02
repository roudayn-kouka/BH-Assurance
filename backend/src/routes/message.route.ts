// src/routes/message.route.ts

import { Router } from 'express';
import { 
  createMessage, 
  getMessageById, 
  getMessagesByConversation,
  validateMessage,
  updateMessageStatus
} from '../controllers/message.controller';
import { authenticate } from '../middleware/auth.middleware';

const router = Router();

// Appliquer l'authentification
router.use(authenticate);

// Routes pour les messages
router.post('/', createMessage);
router.get('/:id', getMessageById);
router.get('/conversations/:conversationId/messages', getMessagesByConversation);
router.patch('/:id/validate', validateMessage);
router.patch('/:id/status', updateMessageStatus);

export default router;