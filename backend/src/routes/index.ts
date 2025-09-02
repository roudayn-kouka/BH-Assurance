import { Router } from 'express';
import authRoute from './auth.route';
import clientRoute from './client.route';
import conversationRoute from './conversation.route';
import messageRoute from './message.route';
import validationRoute from './validation.route';
import analyticsRoute from './analytics.route';
import quoteRoute from './quote.route'; // Nouvelle importation

const router = Router();

// Versioning API
router.use('/auth', authRoute);
router.use('/clients', clientRoute);
router.use('/conversations', conversationRoute);
router.use('/messages', messageRoute);
router.use('/validation', validationRoute);
router.use('/analytics', analyticsRoute);
router.use('/quotes', quoteRoute); // Nouvelle route


// Health check
router.get('/health', (req, res) => {
  res.status(200).json({ status: 'OK', timestamp: new Date() });
});

export default router;