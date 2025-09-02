// src/services/email.service.ts

import nodemailer from 'nodemailer';
import { User } from '../models/user.model';
import dotenv from 'dotenv';

dotenv.config();

// ✅ Configuration du transporteur Nodemailer
const transporter = nodemailer.createTransport({
  service: 'gmail', // ou utilisez 'host', 'port' pour un serveur personnalisé
  host: process.env.SMTP_HOST || 'smtp.gmail.com',
  port: Number(process.env.SMTP_PORT || 587),
  secure: false, // true pour 465, false pour les autres ports
  auth: {
    user: process.env.SMTP_USER,
    pass: process.env.SMTP_PASS
  },
  tls: {
    rejectUnauthorized: false // Utile en dev, à retirer en production
  }
});

// ✅ Vérification que les variables d'environnement sont définies
if (!process.env.SMTP_USER || !process.env.SMTP_PASS) {
  console.warn('⚠️  SMTP_USER ou SMTP_PASS non définis dans .env');
}

if (!process.env.APP_URL) {
  console.warn('⚠️  APP_URL non défini dans .env');
}

// ✅ Template HTML pour les devis
export const quoteTemplate = (quote: any, client: any) => `
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Devis BH Assurance</title>
  <style>
    body {
      font-family: 'Arial', sans-serif;
      line-height: 1.6;
      color: #333;
      background-color: #f9fafb;
      margin: 0;
      padding: 0;
    }
    .container {
      max-width: 650px;
      margin: 20px auto;
      padding: 20px;
      background: white;
      border-radius: 12px;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .header {
      background-color: #2563eb;
      color: white;
      padding: 20px;
      text-align: center;
      border-radius: 12px 12px 0 0;
    }
    .header h1 {
      margin: 0;
      font-size: 24px;
    }
    .content {
      padding: 20px;
      border: 1px solid #e2e8f0;
      border-top: none;
      border-radius: 0 0 12px 12px;
    }
    .greeting {
      font-size: 16px;
      margin-bottom: 16px;
    }
    .intro {
      margin-bottom: 20px;
      color: #4b5563;
    }
    .products {
      width: 100%;
      border-collapse: collapse;
      margin: 20px 0;
      font-size: 14px;
    }
    .products th, .products td {
      border: 1px solid #e2e8f0;
      padding: 10px;
      text-align: left;
    }
    .products th {
      background-color: #f7fafc;
      font-weight: bold;
    }
    .total {
      font-weight: bold;
      text-align: right;
      padding-top: 10px;
      margin-top: 10px;
      border-top: 1px solid #e2e8f0;
    }
    .validity {
      margin: 15px 0;
      font-style: italic;
      color: #6b7280;
    }
    .button {
      display: inline-block;
      background-color: #2563eb;
      color: white;
      padding: 12px 24px;
      text-decoration: none;
      border-radius: 6px;
      font-weight: bold;
      margin: 20px 0 10px;
    }
    .footer {
      margin-top: 30px;
      text-align: center;
      color: #6b7280;
      font-size: 0.9em;
      border-top: 1px solid #e2e8f0;
      padding-top: 20px;
    }
    .footer p {
      margin: 5px 0;
    }
    @media (max-width: 600px) {
      .container {
        margin: 10px;
        padding: 15px;
      }
      .button {
        display: block;
        text-align: center;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Devis BH Assurance</h1>
    </div>
    
    <div class="content">
      <p class="greeting">Bonjour ${client.first_name || client.nom} ${client.last_name || client.prenom},</p>
      
      <p class="intro">
        Merci de votre intérêt pour nos services d'assurance. 
        Voici le devis détaillé pour vos besoins :
      </p>
      
      <table class="products">
        <thead>
          <tr>
            <th>Produit</th>
            <th>Description</th>
            <th>Qté</th>
            <th>Prix unitaire</th>
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          ${quote.products.map((product: any) => `
            <tr>
              <td><strong>${product.name}</strong></td>
              <td>${product.description || '-'}</td>
              <td>${product.quantity}</td>
              <td>${product.price.toFixed(2)} DT</td>
              <td>${(product.price * product.quantity).toFixed(2)} DT</td>
            </tr>
          `).join('')}
        </tbody>
      </table>
      
      <div class="total">
        <p><strong>Total TTC :</strong> ${quote.total_amount.toFixed(2)} DT</p>
        <p><strong>Valable jusqu'au :</strong> ${new Date(quote.valid_until).toLocaleDateString('fr-TN')}</p>
      </div>
      
      <p class="validity">
        Ce devis est valable pendant 15 jours à compter de la date d'envoi.
      </p>
      
      <a href="${process.env.APP_URL}/devis/${quote._id}/accept" class="button">Accepter ce devis</a>
      
      <p>
        Si vous avez des questions ou besoin d'informations supplémentaires, 
        n'hésitez pas à nous contacter.
      </p>
      
      <p>
        Cordialement,<br>
        <strong>L'équipe BH Assurance</strong>
      </p>
    </div>
    
    <div class="footer">
      <p>BH Assurance • +216 71 000 000 • support@bh-assurance.tn</p>
      <p>© ${new Date().getFullYear()} BH Assurance. Tous droits réservés.</p>
    </div>
  </div>
</body>
</html>
`;

// ✅ Envoyer un email avec devis
export const sendQuoteEmail = async (quote: any, client: any): Promise<boolean> => {
  try {
    if (!client?.email) {
      console.error('❌ Email du client manquant');
      return false;
    }

    const mailOptions = {
      from: `"BH Assurance" <${process.env.SMTP_USER}>`,
      to: client.email,
      subject: `Devis BH Assurance - Réf: QUOTE-${quote._id.toString().substr(-6)}`,
      html: quoteTemplate(quote, client)
    };

    await transporter.sendMail(mailOptions);
    console.log(`✅ Devis envoyé avec succès à ${client.email}`);
    return true;
  } catch (error) {
    console.error('❌ Erreur lors de l\'envoi du devis:', error);
    return false;
  }
};

// ✅ Envoyer une notification de validation aux administrateurs
export const sendValidationNotification = async (messageId: string, clientEmail: string): Promise<void> => {
  try {
    const mailOptions = {
      from: `"BH Assurance" <${process.env.SMTP_USER}>`,
      to: process.env.VALIDATOR_EMAIL || 'validator@bh-assurance.tn', // Configurable
      subject: '🔔 BH Assurance — Nouveau message à valider',
      html: `
        <h2 style="color: #1f2937;">Nouveau message à valider</h2>
        <p>Un nouveau message du client <strong>${clientEmail}</strong> est en attente de validation par l'agent IA.</p>
        <p>
          <a href="${process.env.APP_URL}/validation" style="color: #2563eb; text-decoration: none; font-weight: bold;">
            🔗 Cliquez ici pour accéder à la validation
          </a>
        </p>
        <p style="color: #6b7280; font-size: 0.9em;">
          Ce message a été généré automatiquement. Merci de ne pas y répondre.
        </p>
      `
    };

    await transporter.sendMail(mailOptions);
    console.log(`✅ Notification envoyée pour le message ${messageId}`);
  } catch (error) {
    console.error('❌ Erreur lors de l\'envoi de la notification de validation:', error);
    throw new Error('Impossible d\'envoyer la notification de validation');
  }
};

// ✅ Envoyer un email standard (utilitaire)
export const sendEmail = async (options: {
  to: string;
  subject: string;
  text?: string;
  html?: string;
}): Promise<boolean> => {
  try {
    const mailOptions = {
      from: `"BH Assurance" <${process.env.SMTP_USER}>`,
      to: options.to,
      subject: options.subject,
      text: options.text,
      html: options.html
    };

    await transporter.sendMail(mailOptions);
    return true;
  } catch (error) {
    console.error('❌ Erreur lors de l\'envoi de l\'email:', error);
    return false;
  }
};