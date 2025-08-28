const mongoose = require('mongoose');

const messageSchema = new mongoose.Schema({
  conversationId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Conversation',
    required: true
  },
  expediteur: {
    type: String,
    enum: ['client', 'agent'],
    required: true
  },
  type: {
    type: String,
    enum: ['email', 'chat', 'telephone'],
    required: true
  },
  sujet: {
    type: String,
    trim: true
  },
  corps: {
    type: String,
    required: true
  },
  statut: {
    type: String,
    enum: ['en_attente', 'valide', 'rejete', 'envoye'],
    default: 'en_attente'
  },
  dateEnvoi: {
    type: Date
  },
  justification: {
    type: String,
    trim: true
  },
  modifiePar: {
    type: String,
    trim: true
  },
  dateModification: {
    type: Date
  }
}, {
  timestamps: true
});

// Index pour améliorer les performances
messageSchema.index({ conversationId: 1, createdAt: -1 });
messageSchema.index({ statut: 1 });
messageSchema.index({ expediteur: 1 });

module.exports = mongoose.model('Message', messageSchema);
