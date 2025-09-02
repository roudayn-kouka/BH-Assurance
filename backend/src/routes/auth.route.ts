// src/routes/auth.route.ts

import { Router } from 'express';
import { login } from '../controllers/auth.controller'; // ✅ Import correct

const router = Router();

// ✅ Assurez-vous que `login` est une fonction exportée
router.post('/login', login);

export default router;