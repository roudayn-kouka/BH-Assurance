import { Schema, model, Types } from 'mongoose';

const ConversationSchema = new Schema({
  client_id: {
    type: Types.ObjectId,
    ref: 'Client',
    required: true,
    index: true
  },
  status: {
    type: String,
    enum: [
      'nouvelle_opportunite',
      'renouvellement',
      'upsell_cross_sell',
      'resiliation',
      'reclamation',
      'support_information',
      'prospect_froid',
      'perte_client'
    ],
    default: 'support_information'
  },
  is_completed: {
    type: Boolean,
    default: false
  },
  started_at: {
    type: Date,
    default: () => new Date()
  },
  last_activity_at: {
    type: Date,
    default: () => new Date(),
    index: true
  }
}, { 
  timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' } 
});

export default model('Conversation', ConversationSchema);