const mongoose = require('mongoose');

const clientSchema = new mongoose.Schema({
  nom: {
    type: String,
    required: true,
    trim: true
  },
  email: {
    type: String,
    required: true,
    unique: true,
    lowercase: true,
    trim: true
  },
  telephone: {
    type: String,
    required: true,
    trim: true
  },
  dateCreation: {
    type: Date,
    default: Date.now
  },
  statut: {
    type: String,
    enum: ['actif', 'inactif', 'en_attente'],
    default: 'actif'
  }
}, {
  timestamps: true
});

// Index pour améliorer les performances de recherche
clientSchema.index({ email: 1 });
clientSchema.index({ nom: 1 });

module.exports = mongoose.model('Client', clientSchema);