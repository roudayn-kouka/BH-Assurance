// src/models/user.model.ts

import { Document, Schema, model } from 'mongoose';
import bcrypt from 'bcryptjs';

export interface IUser extends Document {
  email: string;
  password: string;
  role: 'admin' | 'validator' | 'viewer';
  createdAt: Date;
  updatedAt: Date;
}

const UserSchema = new Schema<IUser>(
  {
    email: {
      type: String,
      required: [true, 'L’email est requis'],
      unique: true,
      trim: true,
      lowercase: true,
      match: [/^\w+([.-]?\w+)*@\w+([.-]?\w+)*(\.\w{2,})+$/, 'Veuillez entrer un email valide']
    },
    password: {
      type: String,
      required: [true, 'Le mot de passe est requis'],
      minlength: [6, 'Le mot de passe doit contenir au moins 6 caractères'],
      select: false // Ne jamais retourner le mot de passe
    },
    role: {
      type: String,
      enum: {
        values: ['admin', 'validator', 'viewer'],
        message: 'Le rôle doit être parmi: admin, validator, viewer'
      },
      default: 'viewer'
    }
  },
  {
    timestamps: true
  }
);

// ✅ Ajouter la méthode comparePassword
UserSchema.methods.comparePassword = async function (
  candidatePassword: string
): Promise<boolean> {
  return bcrypt.compare(candidatePassword, this.password);
};

// ✅ Supprimer le mot de passe avant de renvoyer l'utilisateur
UserSchema.methods.toJSON = function () {
  const user = this.toObject();
  delete user.password;
  return user;
};

// ✅ Exporter le modèle
export const User = model<IUser>('User', UserSchema);