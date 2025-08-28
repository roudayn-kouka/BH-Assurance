const express = require('express');
const router = express.Router();

// Route simple pour tester
router.get('/', (req, res) => {
  res.json({ message: 'Endpoint conversations - en développement' });
});

router.get('/:id', (req, res) => {
  res.json({ message: `Détails de la conversation ${req.params.id} - en développement` });
});

module.exports = router;