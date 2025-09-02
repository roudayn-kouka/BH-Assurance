import { Router } from 'express';
import { 
  createQuote, 
  sendQuote, 
  updateQuoteStatus,
  getQuoteById,
  getQuotesByConversation
} from '../controllers/quote.controller';
import { authenticate, authorize } from '../middleware/auth.middleware';

const router = Router();

// Routes publiques avec limitation de débit
router.use(authenticate);

// Routes pour les devis
router.post('/', createQuote);
router.get('/:id', getQuoteById);
router.post('/:id/send', sendQuote);
router.patch('/:id/status', updateQuoteStatus);
router.get('/conversation/:conversationId', getQuotesByConversation);

export default router;