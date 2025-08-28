const express = require('express');
const router = express.Router();

// Route simple pour tester
router.get('/', (req, res) => {
  res.json({ message: 'Endpoint clients - en développement' });
});

router.get('/:id', (req, res) => {
  res.json({ message: `Détails du client ${req.params.id} - en développement` });
});

module.exports = router;