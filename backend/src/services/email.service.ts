import nodemailer from 'nodemailer';
import { Types } from 'mongoose';

export const sendValidationNotification = async (messageId: string, clientEmail: string) => {
  try {
    const transporter = nodemailer.createTransport({
      host: process.env.SMTP_HOST,
      port: Number(process.env.SMTP_PORT || 587),
      secure: false,
      auth: {
        user: process.env.SMTP_USER,
        pass: process.env.SMTP_PASS
      }
    });

    const html = `
      <h2>Nouveau message à valider</h2>
      <p>Un nouveau message de <strong>${clientEmail}</strong> est en attente de validation.</p>
      <p><a href="${process.env.APP_URL}/validation/${messageId}">Cliquez ici pour valider le message</a></p>
      <p>Ce message a été généré automatiquement. Merci de ne pas y répondre.</p>
    `;

    await transporter.sendMail({
      from: `"BH Assurance" <${process.env.SMTP_USER}>`,
      to: 'validator@bh-assurance.tn', // À remplacer par l'email des validateurs
      subject: 'BH Assurance — Nouveau message à valider',
      html
    });

    console.log(`Notification envoyée pour le message ${messageId}`);
  } catch (error) {
    console.error('Erreur lors de l\'envoi de la notification:', error);
    throw error;
  }
};