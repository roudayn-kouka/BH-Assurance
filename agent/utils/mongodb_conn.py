from pymongo import MongoClient, errors
import os
from dotenv import load_dotenv
from bson import ObjectId
from datetime import datetime

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
    statut: str = "valide",
    msg_type: str = "chat",
    conversation_id: str = None,
    sujet: str = "Nouvelle conversation",
):
    """
    Append a message to a conversation in the database.
    If no conversation_id is provided, creates a new conversation for the client.

    :param client_id: The _id of the client (string)
    :param corps: Message content
    :param expediteur: "client" or "agent"
    :param statut: Message status (default "valide")
    :param msg_type: Message type (default "chat")
    :param conversation_id: The _id of the conversation (string, optional)
    :param sujet: Subject of the conversation if a new one is created
    :return: The inserted message _id
    """
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        db = client.get_database()

        messages_collection = db["messages"]
        conversations_collection = db["conversations"]

        # If no conversation is provided, create a new one
        if not conversation_id:
            conversation_doc = {
                "clientId": client_id,
                "sujet": sujet,
                "statut": "ouverte",
                "dernierContact": datetime.utcnow(),
                "satisfaction": 0,
                "nombreMessages": 0,
            }
            conv_result = conversations_collection.insert_one(conversation_doc)
            conversation_id = conv_result.inserted_id

        # Prepare the message document
        message_doc = {
            "conversationId": conversation_id,
            "expediteur": expediteur,
            "corps": corps,
            "type": msg_type,
            "statut": statut,
            "createdAt": datetime.utcnow(),
        }

        # Insert message
        result = messages_collection.insert_one(message_doc)

        # Update number of messages in the conversation
        conversations_collection.find_one_and_update(
            {"_id": conversation_id},
            {
                "$inc": {"nombreMessages": 1},
                "$set": {"dernierContact": datetime.utcnow()},
            },
        )

        return result.inserted_id, conversation_id

    except errors.ServerSelectionTimeoutError as err:
        print("❌ Connection failed:", err)
        return None, None

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


# Run only if script is executed directly
if __name__ == "__main__":
    conversation = get_first_open_conversation()
    if conversation:
        print("✅ First open conversation:")
        print(conversation)
    else:
        print("⚠️ No open conversation found")
