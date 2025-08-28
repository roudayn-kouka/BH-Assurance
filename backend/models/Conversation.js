const mongoose = require('mongoose');

const conversationSchema = new mongoose.Schema({
  clientId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'Client',
    required: true
  },
  sujet: {
    type: String,
    trim: true
  },
  statut: {
    type: String,
    enum: ['ouverte', 'fermee', 'en_attente'],
    default: 'ouverte'
  },
  dernierContact: {
    type: Date,
    default: Date.now
  },
  nombreMessages: {
    type: Number,
    default: 0
  },
  satisfaction: {
    type: Number,
    min: 0,
    max: 100,
    default: 0
  }
}, {
  timestamps: true
});

// Mettre à jour la date du dernier contact à chaque modification
conversationSchema.pre('save', function(next) {
  if (this.isModified()) {
    this.dernierContact = Date.now();
  }
  next();
});

// Index pour améliorer les performances
conversationSchema.index({ clientId: 1, dernierContact: -1 });
conversationSchema.index({ statut: 1 });

module.exports = mongoose.model('Conversation', conversationSchema);