import { Router } from 'express';
import { login, register } from '../controllers/auth.controller';

const router = Router();

// Public routes
router.post('/login', login);
router.post('/register', register); // Optionnel selon votre besoin

export default router;