import { Router } from 'express';
import { 
  getMessagesByConversation, 
  createMessage, 
  validateMessage 
} from '../controllers/message.controller';
import { authMiddleware } from '../middleware/auth.middleware';
const router = Router();

// Accès aux messages d'une conversation
router.get('/:conversationId/messages', authMiddleware(['validator', 'admin']), getMessagesByConversation);

// Création de message (agents seulement)
router.post('/', authMiddleware(['agent','admin']), createMessage);

// Validation/rejet (validateurs seulement)
router.patch('/:id/validate', authMiddleware(['validator','admin']), validateMessage);

export default router;