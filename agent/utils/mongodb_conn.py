from pymongo import MongoClient, errors
import os
from dotenv import load_dotenv
from bson import ObjectId
from datetime import datetime
import random
# User type classification now handled by API directly

# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/BH")  # adjust DB name


def get_first_open_conversation():
    """
    Connects to MongoDB, fetches the first open conversation with its client and messages,
    and returns it as a dictionary. Returns None if not found or connection fails.
    """
    try:
        # Connect to MongoDB
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")

        db = client.get_database()  # use DB name from URI
        conversations_collection = db["conversations"]
        messages_collection = db["messages"]
        clients_collection = db["clients"]

        # Get the first open conversation
        conv = conversations_collection.find_one({"statut": "ouverte"})
        if not conv:
            return None

        # Get client info
        client_data = clients_collection.find_one({"_id": conv["clientId"]})

        # Get messages for this conversation
        messages = list(
            messages_collection.find({"conversationId": conv["_id"]}).sort(
                "createdAt", 1
            )
        )

        # Build dictionary
        conversation_dict = {
            "conversationId": str(conv["_id"]),
            "client": {
                "id": str(client_data.get("_id")),
                "nom": client_data.get("nom"),
                "email": client_data.get("email"),
            },
            "messages": [
                {
                    "corps": f"{msg.get('expediteur')} : {msg.get('corps')}",
                }
                for msg in messages
            ],
        }

        # Build conversation history string
        conversation_history = "\n".join(
            [f"{msg.get('expediteur')}: {msg.get('corps')}" for msg in messages]
        )

        # Find latest user message
        latest_user_message = None
        for msg in reversed(messages):
            if msg.get("expediteur") == "user":
                latest_user_message = msg.get("corps")
                break

        # Add them to dict
        conversation_dict["conversation_history"] = conversation_history
        conversation_dict["latest_user_message"] = latest_user_message

        return conversation_dict

    except errors.ServerSelectionTimeoutError as err:
        print("❌ Connection failed:", err)
        return None

    finally:
        try:
            client.close()
        except:
            pass


def append_message_to_conversation(
    client_id: str,
    corps: str,
    expediteur: str = "agent",
    statut: str = "pending",
    msg_type: str = "email",
    conversation_id: str = None,
    subject: str = None,
    conversation_status: str = "nouvelle_opportunite",
):
    """
    Append a message to a conversation in the database with backend-compatible schema.
    If no conversation_id is provided, creates a new conversation for the client.

    :param client_id: The _id of the client (string or ObjectId)
    :param corps: Message content (body)
    :param expediteur: "client", "ai", or "agent" (maps to sender in backend)
    :param statut: Message status: "pending", "validated", "rejected" (backend compatible)
    :param msg_type: Message type (not used in backend schema)
    :param conversation_id: The _id of the conversation (string, optional)
    :param subject: Subject of the message
    :param conversation_status: Status for new conversations (backend enum)
    :return: Tuple of (message_id, conversation_id)
    """
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        db = client.get_database()

        messages_collection = db["messages"]
        conversations_collection = db["conversations"]

        # Convert client_id to ObjectId if it's a string
        if isinstance(client_id, str):
            try:
                client_oid = ObjectId(client_id)
            except:
                print(f"❌ Invalid client_id format: {client_id}")
                return None, None
        else:
            client_oid = client_id

        # If no conversation is provided, create a new one using backend schema
        if not conversation_id:
            conversation_doc = {
                "client_id": client_oid,  # Backend uses client_id, not clientId
                "status": conversation_status,  # Backend enum values
                "is_completed": False,
                "conversation_status": "pending",  # Default to pending when creating new conversations
                "started_at": datetime.utcnow(),
                "last_activity_at": datetime.utcnow(),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            conv_result = conversations_collection.insert_one(conversation_doc)
            conversation_id = conv_result.inserted_id
            print(f"✅ Created new conversation: {conversation_id}")
        else:
            # Convert conversation_id to ObjectId if it's a string
            if isinstance(conversation_id, str):
                try:
                    conversation_id = ObjectId(conversation_id)
                except:
                    print(f"❌ Invalid conversation_id format: {conversation_id}")
                    return None, None

        # Determine message direction based on sender
        direction = "sent" if expediteur in ["agent", "ai"] else "inbox"

        # Prepare the message document using backend schema
        message_doc = {
            "conversation_id": conversation_id,  # Backend uses conversation_id
            "sender": expediteur,  # Backend field name
            "direction": direction,  # Required in backend
            "subject": subject,  # Backend field name
            "body": corps,  # Backend field name
            "status": statut,  # Backend status enum
            "is_modified": False,  # Default value
            "created_at": datetime.utcnow(),  # Backend timestamp field
        }

        # Insert message
        result = messages_collection.insert_one(message_doc)
        print(f"✅ Created message: {result.inserted_id} from {expediteur}")

        # Update conversation activity using backend schema
        conversations_collection.find_one_and_update(
            {"_id": conversation_id},
            {
                "$set": {
                    "last_activity_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                },
            },
        )

        return result.inserted_id, conversation_id

    except errors.ServerSelectionTimeoutError as err:
        print("❌ Connection failed:", err)
        return None, None
    except Exception as e:
        print(f"❌ Error in append_message_to_conversation: {e}")
        return None, None

    finally:
        try:
            client.close()
        except:
            pass


def get_conversations_with_open_status():
    """
    Connects to MongoDB, fetches all conversations with conversation_status='open',
    along with their client and messages, and returns them as a list.
    Returns empty list if none found or connection fails.
    """
    try:
        # Connect to MongoDB
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")

        db = client.get_database()  # use DB name from URI
        conversations_collection = db["conversations"]
        messages_collection = db["messages"]
        clients_collection = db["clients"]

        # Get conversations with conversation_status='open'
        open_conversations = list(conversations_collection.find({"conversation_status": "open"}))
        
        if not open_conversations:
            return []

        conversation_list = []
        
        for conv in open_conversations:
            # Get client info
            client_data = clients_collection.find_one({"_id": conv["client_id"]})
            if not client_data:
                continue  # Skip if client not found
            
            # Get messages for this conversation
            messages = list(
                messages_collection.find({"conversation_id": conv["_id"]}).sort(
                    "created_at", 1
                )
            )

            # Build conversation history string
            conversation_history = "\n".join(
                [f"{msg.get('sender', 'unknown')}: {msg.get('body', '')}" for msg in messages]
            )

            # Find latest client message
            latest_client_message = None
            for msg in reversed(messages):
                if msg.get("sender") == "client":
                    latest_client_message = msg.get("body")
                    break

            # Build dictionary for this conversation
            conversation_dict = {
                "conversation_id": str(conv["_id"]),
                "client": {
                    "id": str(client_data.get("_id")),
                    "first_name": client_data.get("first_name"),
                    "last_name": client_data.get("last_name"),
                    "email": client_data.get("email"),
                    "phone": client_data.get("phone"),
                },
                "status": conv.get("status"),
                "conversation_status": conv.get("conversation_status"),
                "is_completed": conv.get("is_completed", False),
                "last_activity_at": conv.get("last_activity_at"),
                "messages": [
                    {
                        "sender": msg.get("sender"),
                        "body": msg.get("body"),
                        "created_at": msg.get("created_at"),
                        "status": msg.get("status")
                    }
                    for msg in messages
                ],
                "conversation_history": conversation_history,
                "latest_client_message": latest_client_message,
            }
            
            conversation_list.append(conversation_dict)

        return conversation_list

    except errors.ServerSelectionTimeoutError as err:
        print("❌ Connection failed:", err)
        return []

    finally:
        try:
            client.close()
        except:
            pass


def get_first_open_status_conversation():
    """
    Get the first conversation with conversation_status='open'.
    Returns None if no open conversation found.
    """
    conversations = get_conversations_with_open_status()
    return conversations[0] if conversations else None


def update_conversation_status(conversation_id: str, new_status: str) -> bool:
    """
    Update the conversation_status field for a given conversation.
    
    :param conversation_id: The _id of the conversation (string or ObjectId)
    :param new_status: New status ('open' or 'pending')
    :return: True if successful, False otherwise
    """
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        db = client.get_database()
        
        conversations_collection = db["conversations"]
        
        # Convert conversation_id to ObjectId if it's a string
        if isinstance(conversation_id, str):
            try:
                conversation_oid = ObjectId(conversation_id)
            except:
                print(f"❌ Invalid conversation_id format: {conversation_id}")
                return False
        else:
            conversation_oid = conversation_id
        
        # Validate new status
        if new_status not in ['open', 'pending']:
            print(f"❌ Invalid status: {new_status}. Must be 'open' or 'pending'")
            return False
        
        # Update conversation status
        result = conversations_collection.find_one_and_update(
            {"_id": conversation_oid},
            {
                "$set": {
                    "conversation_status": new_status,
                    "updated_at": datetime.utcnow(),
                    "last_activity_at": datetime.utcnow(),
                }
            },
            return_document=True
        )
        
        if result:
            print(f"✅ Updated conversation {conversation_id} status to: {new_status}")
            return True
        else:
            print(f"❌ Conversation {conversation_id} not found")
            return False
    
    except errors.ServerSelectionTimeoutError as err:
        print("❌ Connection failed:", err)
        return False
    except Exception as e:
        print(f"❌ Error updating conversation status: {e}")
        return False
    
    finally:
        try:
            client.close()
        except:
            pass


def has_open_conversation() -> bool:
    """
    Check if there is at least one open conversation in the database.
    Returns True if one exists, otherwise False.
    """
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = client.get_database()
        conversations_collection = db["conversations"]

        return conversations_collection.find_one({"statut": "ouverte"}) is not None

    except errors.ServerSelectionTimeoutError as err:
        print("❌ Connection failed:", err)
        return False
    finally:
        try:
            client.close()
        except:
            pass


def create_or_get_client(user_data: dict) -> str:
    """
    Create or get a client from the database based on user_data using API provided user_type.
    Returns the client ObjectId as string.
    
    :param user_data: Dictionary containing user information from AI agent with API user_type
    :return: Client ObjectId as string, or None if error
    """
    try:
        mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        mongo_client.admin.command("ping")
        db = mongo_client.get_database()
        clients_collection = db["clients"]
        
        # Get user type directly from API response
        raw_data = user_data.get("data", {})
        profile = raw_data.get("profile", {})
        user_type = raw_data.get("user_type", "unknown")
        
        print(f"🔍 User type from API: {user_type}")
        
        # Map API user_type to client_type
        if user_type == "personne_physique":
            client_type = "individual"
        elif user_type == "personne_morale":
            client_type = "company"
        else:
            client_type = "individual"  # Default fallback
            
        # Extract basic information from profile
        email = profile.get("email")
        user_id = raw_data.get("user_id")
        
        # Generate email if not provided
        if not email and user_id:
            email = f"user_{user_id}@generated.local"
        elif not email:
            print("❌ No email or user_id found in user_data")
            return None
            
        # Check if client already exists
        existing_client = clients_collection.find_one({"email": email})
        if existing_client:
            print(f"✅ Found existing client: {existing_client['_id']}")
            return str(existing_client["_id"])
            
        # Extract name information based on user type
        if client_type == "company":
            # For companies
            company_name = profile.get("company_name", profile.get("raison_sociale", "Unknown Company"))
            first_name = profile.get("contact_person", profile.get("first_name", company_name))
            last_name = f"({company_name})"
        else:
            # For individuals
            first_name = profile.get("first_name", profile.get("prenom", "Unknown"))
            last_name = profile.get("last_name", profile.get("nom", "Unknown"))
            
        # Extract other basic fields
        phone = profile.get("telephone", profile.get("phone"))
        age = profile.get("age")
        matricule_fiscale = profile.get("matricule_fiscale")
        
        # Extract job/profession information
        if client_type == "company":
            job = profile.get("lib_secteur_activite", profile.get("lib_activite", "Unknown Business"))
        else:
            job = profile.get("profession", profile.get("lib_activite", "Unknown"))
            
        # Generate unique bd_id
        bd_id = user_id
        if not bd_id or not str(bd_id).isdigit():
            bd_id = random.randint(100000, 999999)
        else:
            bd_id = int(bd_id)
        
        # Ensure bd_id is unique
        while clients_collection.find_one({"bd_id": bd_id}):
            bd_id = random.randint(100000, 999999)
            
        # Create contracts array from profile data
        contracts = []
        current_product = profile.get("lib_produit")
        recommended_product = profile.get("recommended_product", profile.get("candidate_produit"))
        
        # Add current product as active contract
        if current_product:
            contract = {
                "type": current_product,
                "number": f"CONTRACT_{bd_id}_1",
                "start_at": datetime.utcnow(),
                "status": "active",
                "premium": random.randint(300, 2000)
            }
            contracts.append(contract)
                
        # Add recommended product as prospect contract
        if recommended_product and recommended_product != current_product:
            contract = {
                "type": recommended_product,
                "number": f"PROSPECT_{bd_id}_1",
                "start_at": datetime.utcnow(),
                "status": "prospect",
                "premium": random.randint(400, 3000),
                "confidence_score": 0.75  # Default confidence
            }
            contracts.append(contract)
                
        # Calculate simple opportunity score
        opportunity_score = 50  # Base score
        if recommended_product:
            opportunity_score += 25
        if profile.get("good_buyer_score_pct"):
            try:
                buyer_score = float(profile.get("good_buyer_score_pct", 0))
                if buyer_score > 50:
                    opportunity_score += 15
            except:
                pass
        
        # Build client document matching backend schema
        client_doc = {
            "email": email,
            "phone": phone,
            "first_name": first_name,
            "last_name": last_name,
            "age": int(age) if age and str(age).replace('.', '').isdigit() else None,
            "job": job,
            "bd_id": bd_id,
            "contracts": contracts,
            "opportunity_score": opportunity_score,
            "last_contact_at": datetime.utcnow(),
            "client_type": client_type,
            "classification_confidence": 1.0,  # High confidence from API
            "fiscal_id": matricule_fiscale,
        }
        
        # Add company-specific fields if applicable
        if client_type == "company":
            client_doc.update({
                "company_name": profile.get("company_name", profile.get("raison_sociale")),
                "sector": profile.get("lib_secteur_activite"),
                "employee_count": profile.get("nb_employees"),
            })
            
        # Remove None values
        client_doc = {k: v for k, v in client_doc.items() if v is not None}
        
        # Insert client
        result = clients_collection.insert_one(client_doc)
        print(f"✅ Created new {client_type} client: {result.inserted_id}")
        print(f"   Name: {first_name} {last_name}")
        
        return str(result.inserted_id)
        
    except errors.ServerSelectionTimeoutError as err:
        print("❌ Connection failed:", err)
        return None
    except Exception as e:
        print(f"❌ Error creating client: {e}")
        return None
    finally:
        try:
            mongo_client.close()
        except:
            pass


# Run only if script is executed directly
if __name__ == "__main__":
    conversation = get_first_open_conversation()
    if conversation:
        print("✅ First open conversation:")
        print(conversation)
    else:
        print("⚠️ No open conversation found")
