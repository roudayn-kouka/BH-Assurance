// src/models/conversation.model.ts

import mongoose, { Document, Schema } from 'mongoose';

export interface IConversation extends Document {
  client_id: mongoose.Types.ObjectId;
  status: 
    | 'active'
    | 'renouvellement'
    | 'completed'
    | 'failed'
    | 'success'
    | 'resiliation'
    | 'new_opportunity'
    | 'upsell_cross_sell'
    | 'support_information'
    | 'reclamation'
    | 'prospect_froid'
    | 'perte_client'
    | 'blocked';
  subject: string;
  is_completed: boolean;
  completion_reason?: string;
  created_at: Date;
  last_activity_at: Date;
  last_message_at: Date;
  message_count: number;
  opportunity_score: number;
}

const ConversationSchema = new Schema<IConversation>({
  client_id: { type: Schema.Types.ObjectId, ref: 'Client', required: true },
  status: { 
    type: String,
    enum: [
      'active',
      'completed',
      'failed',
      'success',
      'resiliation',
      'new_opportunity',
      'upsell_cross_sell',
      'support_information',
      'reclamation',
      'prospect_froid',
      'perte_client'
    ],
    default: 'active',
    required: true 
  },
  subject: { type: String, default: 'Nouvelle conversation' },
  is_completed: { type: Boolean, default: false },
  completion_reason: { type: String },
  created_at: { type: Date, default: Date.now },
  last_activity_at: { type: Date, default: Date.now },
  message_count: { type: Number, default: 0 },
  opportunity_score: { type: Number, default: 0 }
});

export default mongoose.model<IConversation>('Conversation', ConversationSchema);