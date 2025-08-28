const Message = require('../models/Message');
const Conversation = require('../models/Conversation');
const { sendValidatedResponse } = require('../utils/emailService');

// [Vos autres fonctions restent inchangées...]

// Valider un message
exports.validateMessage = async (req, res) => {
  try {
    const { justification } = req.body;
    
    const message = await Message.findById(req.params.id)
      .populate({
        path: 'conversationId',
        populate: {
          path: 'clientId',
          select: 'nom email telephone'
        }
      });
    
    if (!message) {
      return res.status(404).json({ message: 'Message non trouvé' });
    }

    // Envoyer l'email via SendGrid
    try {
      await sendValidatedResponse(
        message.conversationId.clientId.email,
        message.conversationId.clientId.nom,
        message.corps,
        message.sujet || "Question client"
      );
      
      // Mettre à jour le message après l'envoi réussi
      message.statut = 'valide';
      message.dateEnvoi = Date.now();
      message.justification = justification;
      message.modifiePar = 'Administrateur';
      
      await message.save();
      
      res.json({
        success: true,
        message: 'Message validé et email envoyé avec succès',
        data: message
      });
    } catch (emailError) {
      console.error('Erreur email:', emailError);
      res.status(500).json({ 
        success: false,
        message: 'Message validé mais échec de l\'envoi de l\'email',
        error: emailError.message 
      });
    }
  } catch (error) {
    res.status(400).json({ 
      success: false,
      message: error.message 
    });
  }
};