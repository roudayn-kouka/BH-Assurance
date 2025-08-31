import { Schema, model } from 'mongoose';

const UserSchema = new Schema({
  email: { 
    type: String, 
    required: true, 
    unique: true 
  },
  password: { 
    type: String, 
    required: true 
  },
  role: {
    type: String,
    enum: ['admin', 'validator', 'viewer'],
    default: 'viewer'
  }
}, { 
  timestamps: true 
});

export default model('User', UserSchema);