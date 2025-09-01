import { Router } from 'express';
import { getValidationQueue } from '../controllers/validation.controller';
import { authMiddleware } from '../middleware/auth.middleware';
const router = Router();

import { authenticate, authorize } from '../middleware/auth.middleware';

// ✅ Seuls les 'admin' peuvent accéder à la file de validation
router.get('/queue', authenticate, authorize(['admin']), getValidationQueue);


export default router;