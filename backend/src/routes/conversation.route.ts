import { Router } from 'express';
import { 
  getAllConversations, 
  getConversationById, 
  createConversation, 
  updateConversation 
} from '../controllers/conversation.controller';
import { authMiddleware } from '../middleware/auth.middleware';
const router = Router();

// Routes accessibles aux validateurs et admins
router.get('/', authMiddleware(['validator', 'admin']), getAllConversations);
router.get('/:id', authMiddleware(['validator', 'admin']), getConversationById);

// Création par les agents
router.post('/', authMiddleware(['agent','admin']), createConversation);

// Mise à jour du statut par les validateurs
router.patch('/:id', authMiddleware(['validator', 'admin']), updateConversation);

export default router;