import { Router } from 'express';
import { 
  getAllClients, 
  getClientById, 
  createClient, 
  updateClient, 
  getClientProfile 
} from '../controllers/client.controller';
import { authMiddleware } from '../middleware/auth.middleware';
const router = Router();

// Routes accessibles aux validateurs et admins
router.get('/', authMiddleware(['validator', 'admin']), getAllClients);
router.get('/:id', authMiddleware(['validator', 'admin']), getClientById);
router.post('/', authMiddleware(['admin']), createClient);
router.put('/:id', authMiddleware(['admin']), updateClient);

// Route spécifique pour le profil complet
router.get('/:id/profile', authMiddleware(['validator', 'admin']), getClientProfile);

export default router;