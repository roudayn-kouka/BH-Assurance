// src/routes/conversation.route.ts

import { Router } from 'express';
import { 
  getConversations, 
  getConversationById, 
  createConversation, 
  completeConversation 
} from '../controllers/conversation.controller';
import { authenticate } from '../middleware/auth.middleware';

const router = Router();

// Appliquer l'authentification
router.use(authenticate);

// Routes
router.get('/conversations', getConversations);
router.get('/conversations/:id', getConversationById);
router.post('/conversations', createConversation);
router.post('/conversations/:id/complete', completeConversation);

export default router;