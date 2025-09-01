import { Router } from 'express';
import { 
  getAnalyticsSummary, 
  getTimeSeriesAnalytics 
} from '../controllers/analytics.controller';
import { authMiddleware } from '../middleware/auth.middleware';
const router = Router();

// Accès aux métriques (admins et validateurs)
router.get('/summary', authMiddleware(['admin', 'validator']), getAnalyticsSummary);
router.get('/time-series', authMiddleware(['admin', 'validator']), getTimeSeriesAnalytics);

export default router;