const sgMail = require('@sendgrid/mail');
require('dotenv').config();

// Configuration de SendGrid
sgMail.setApiKey(process.env.SENDGRID_API_KEY);

// Fonction pour envoyer un email
const sendEmail = async (to, subject, html) => {
  try {
    const msg = {
      to,
      from: process.env.EMAIL_FROM,
      subject,
      html,
    };

    const result = await sgMail.send(msg);
    console.log('Email envoyé avec succès à:', to);
    return { success: true, messageId: result[0].headers['x-message-id'] };
  } catch (error) {
    console.error('Erreur SendGrid:', error.response?.body || error.message);
    throw new Error(`Échec de l'envoi de l'email: ${error.message}`);
  }
};

// Fonction pour envoyer une réponse validée
const sendValidatedResponse = async (clientEmail, clientName, response, question) => {
  const subject = 'Réponse de BH Assurance à votre demande';
  const html = `
    <div style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
      <div style="background-color: #0056b3; padding: 20px; text-align: center; color: white;">
        <h1>BH Assurance</h1>
      </div>
      
      <div style="padding: 20px; background-color: #f9f9f9;">
        <h2 style="color: #0056b3;">Réponse à votre demande</h2>
        <p>Cher(e) <strong>${clientName}</strong>,</p>
        <p>Nous vous remercions d'avoir contacté BH Assurance.</p>
        
        <div style="background-color: #fff; padding: 15px; border-left: 4px solid #0056b3; margin: 20px 0;">
          <p><strong>Votre question:</strong> ${question}</p>
          <p><strong>Notre réponse:</strong></p>
          <div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px;">
            ${response}
          </div>
        </div>
        
        <p>Si vous avez d'autres questions, n'hésitez pas à nous contacter.</p>
        
        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd;">
          <p>Cordialement,<br>
          <strong>L'équipe BH Assurance</strong></p>
          <p style="font-size: 12px; color: #999;">
            Tél: +216 70 123 456<br>
            Email: support@bh-assurance.tn
          </p>
        </div>
      </div>
      
      <div style="background-color: #333; color: #fff; padding: 15px; text-align: center; font-size: 12px;">
        <p>Cet email a été envoyé automatiquement. Merci de ne pas y répondre.</p>
      </div>
    </div>
  `;

  return await sendEmail(clientEmail, subject, html);
};

module.exports = {
  sendEmail,
  sendValidatedResponse
};