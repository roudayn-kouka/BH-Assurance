import { Schema, model, Types } from 'mongoose';

const MessageSchema = new Schema({
  conversation_id: {
    type: Types.ObjectId,
    ref: 'Conversation',
    required: true,
    index: true
  },
  sender: {
    type: String,
    enum: ['client', 'ai', 'agent'],
    required: true
  },
  direction: {
    type: String,
    enum: ['inbox', 'sent'],
    required: true
  },
  subject: String,
  body: { type: String, required: true },
  status: {
    type: String,
    enum: ['pending', 'validated', 'rejected'],
    default: 'pending'
  },
  is_modified: { type: Boolean, default: false },
  validated_by: { type: Types.ObjectId, ref: 'User' },
  validated_at: Date,
  original_body: String
}, { 
  timestamps: { createdAt: 'created_at' } 
});

// Index pour trier par date descendante
MessageSchema.index({ created_at: -1 });

export default model('Message', MessageSchema);