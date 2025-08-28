const express = require('express');
const router = express.Router();

// Route simple pour tester
router.get('/', (req, res) => {
  res.json({ message: 'Endpoint messages - en développement' });
});

router.get('/pending', (req, res) => {
  res.json({ message: 'Messages en attente - en développement' });
});

router.get('/:id', (req, res) => {
  res.json({ message: `Détails du message ${req.params.id} - en développement` });
});

module.exports = router;