import { Schema, model } from 'mongoose';

// Sous-schéma pour les contrats
const ContractSchema = new Schema({
  type: { type: String, required: true }, // Ex: "auto", "habitation"
  number: String,
  start_at: Date,
  end_at: Date,
  premium: Number,
  status: {
    type: String,
    enum: ['active', 'expired', 'cancelled'],
    default: 'active'
  }
});

// Schéma principal Client
const ClientSchema = new Schema({
  email: { 
    type: String, 
    required: true, 
    unique: true, 
    index: true 
  },
  phone: String,
  first_name: String,
  last_name: String,
  age: Number,
  job: String,
  contracts: [ContractSchema],
  opportunity_score: {
    type: Number,
    default: 0
  },
  last_contact_at: Date
}, { 
  timestamps: { createdAt: 'created_at', updatedAt: 'updated_at' } 
});

export default model('Client', ClientSchema);