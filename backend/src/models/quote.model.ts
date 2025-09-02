import mongoose, { Document, Schema } from 'mongoose';

export interface IQuoteProduct {
  id: string;
  name: string;
  description: string;
  price: number;
  quantity: number;
  category: string;
}

export interface IQuote extends Document {
  conversation_id: mongoose.Types.ObjectId;
  client_id: mongoose.Types.ObjectId;
  products: IQuoteProduct[];
  total_amount: number;
  valid_until: Date;
  status: 'draft' | 'sent' | 'accepted' | 'rejected' | 'expired';
  created_at: Date;
  updated_at: Date;
  notes?: string;
}

const QuoteProductSchema = new Schema<IQuoteProduct>({
  id: { type: String, required: true },
  name: { type: String, required: true },
  description: { type: String },
  price: { type: Number, required: true },
  quantity: { type: Number, default: 1 },
  category: { type: String }
});

const QuoteSchema = new Schema<IQuote>({
  conversation_id: { type: Schema.Types.ObjectId, ref: 'Conversation', required: true },
  client_id: { type: Schema.Types.ObjectId, ref: 'User', required: true },
  products: { type: [QuoteProductSchema], required: true },
  total_amount: { type: Number, required: true },
  valid_until: { type: Date, required: true },
  status: { 
    type: String, 
    enum: ['draft', 'sent', 'accepted', 'rejected', 'expired'], 
    default: 'draft',
    required: true 
  },
  created_at: { type: Date, default: Date.now },
  updated_at: { type: Date, default: Date.now },
  notes: { type: String }
});

// Calculer le total automatiquement
QuoteSchema.pre('validate', function(next) {
  this.total_amount = this.products.reduce((sum, product) => 
    sum + (product.price * product.quantity), 0);
  this.updated_at = new Date();
  next();
});

export default mongoose.model<IQuote>('Quote', QuoteSchema);