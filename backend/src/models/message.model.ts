// src/models/message.model.ts

import mongoose, { Document, Schema } from 'mongoose';

export interface IMessage extends Document {
  conversation_id: mongoose.Types.ObjectId;
  sender: 'client' | 'agent' | 'ai';
  body: string;
  direction: 'inbox' | 'sent';
  status: 'open' | 'pending' | 'validated' | 'sent' | 'blocked';
  is_client_response: boolean;
  is_modified: boolean; 
  created_at: Date;
  updated_at: Date;
  subject: string;

}

const MessageSchema = new Schema<IMessage>({
  conversation_id: { 
    type: Schema.Types.ObjectId, 
    ref: 'Conversation', 
    required: true 
  },
  sender: { 
    type: String, 
    enum: ['client', 'agent', 'ai'], 
    required: true 
  },
   subject: { 
    type: String, 
    default: '' 
  }, 
  body: { 
    type: String, 
    required: true 
  },
  direction: { 
    type: String, 
    enum: ['inbox', 'sent'], 
    required: true 
  },
  status: { 
    type: String, 
    enum: ['open', 'pending', 'validated', 'sent', 'blocked'], 
    default: 'open',
    required: true 
  },
  is_client_response: { 
    type: Boolean, 
    default: false 
  },
  is_modified: { 
    type: Boolean, 
    default: false 
  }, // ✅ Ajouté ici
  created_at: { 
    type: Date, 
    default: Date.now 
  },
  updated_at: { 
    type: Date, 
    default: Date.now 
  }
});

// Mettre à jour updated_at à chaque sauvegarde
MessageSchema.pre('save', function(next) {
  this.updated_at = new Date();
  next();
});

export default mongoose.model<IMessage>('Message', MessageSchema);