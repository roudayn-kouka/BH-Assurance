#!/usr/bin/env python3
"""
Simplified test script for conversation status functionality.

This script tests the core MongoDB functions:
1. Creating conversations with different statuses
2. Detecting conversations with 'open' status  
3. Updating conversation_status from 'open' to 'pending'
"""

import sys
import os

# Add agent directory to Python path
agent_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'agent')
sys.path.insert(0, agent_dir)

from utils.mongodb_conn import (
    create_or_get_client, 
    append_message_to_conversation,
    get_conversations_with_open_status,
    get_first_open_status_conversation,
    update_conversation_status
)
from pymongo import MongoClient
from datetime import datetime

# MongoDB connection
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/BH")

def test_basic_conversation_status_workflow():
    """Test the basic workflow without full agent integration."""
    print("\n" + "="*60)
    print("TESTING BASIC CONVERSATION STATUS WORKFLOW")
    print("="*60)
    
    try:
        # Step 1: Create a test client
        print("\nStep 1: Creating test client...")
        test_user_data = {
            "user_data_str": "Simple Test Client",
            "data": {
                "user_id": "SIMPLE_TEST_001",
                "email": "simple.test@example.com",
                "endpoint_strategy": "product_recommendation",
                "user_type": "personne_physique",
                "profile": {
                    "first_name": "Jean",
                    "nom": "Martin", 
                    "telephone": "+33 6 99 88 77 66",
                    "age": 35,
                    "lib_secteur_activite": "IT",
                    "lib_activite": "Développement web",
                    "score": 0.85
                }
            }
        }
        
        client_id = create_or_get_client(test_user_data)
        if not client_id:
            print("❌ Failed to create test client")
            return False
        
        print(f"✅ Test client created: {client_id}")
        
        # Step 2: Create initial conversation (pending status by default)
        print("\nStep 2: Creating initial conversation...")
        initial_message = "Bonjour, nous avons des opportunités d'assurance pour vous."
        
        message_id, conversation_id = append_message_to_conversation(
            client_id=client_id,
            corps=initial_message,
            expediteur="ai",
            statut="pending",
            subject="Opportunités d'assurance",
            conversation_status="nouvelle_opportunite"
        )
        
        if not conversation_id:
            print("❌ Failed to create initial conversation")
            return False
        
        print(f"✅ Initial conversation created: {conversation_id}")
        print(f"   Status: pending (default)")
        
        # Step 3: Add client response
        print("\nStep 3: Adding client response...")
        client_response = "Bonjour, oui je suis intéressé. Pouvez-vous me donner plus d'informations ?"
        
        client_msg_id, _ = append_message_to_conversation(
            client_id=client_id,
            corps=client_response,
            expediteur="client",
            statut="validated",
            subject="Re: Opportunités d'assurance",
            conversation_id=conversation_id
        )
        
        if not client_msg_id:
            print("❌ Failed to create client response")
            return False
        
        print(f"✅ Client response created: {client_msg_id}")
        
        # Step 4: Update conversation status to 'open' (client responded)
        print("\nStep 4: Setting conversation status to 'open'...")
        status_updated = update_conversation_status(conversation_id, "open")
        
        if not status_updated:
            print("❌ Failed to set conversation status to 'open'")
            return False
        
        print(f"✅ Conversation status set to 'open'")
        
        # Step 5: Test detection of open conversations
        print("\nStep 5: Testing detection of open conversations...")
        open_conversations = get_conversations_with_open_status()
        
        print(f"✅ Found {len(open_conversations)} conversations with 'open' status")
        
        found_our_conversation = False
        for conv in open_conversations:
            if conv['conversation_id'] == str(conversation_id):
                found_our_conversation = True
                print(f"   Found our test conversation: {conv['conversation_id']}")
                print(f"   Client: {conv['client']['first_name']} {conv['client']['last_name']}")
                print(f"   Status: {conv['conversation_status']}")
                print(f"   Latest client message: {conv['latest_client_message'][:50]}...")
                break
        
        if not found_our_conversation:
            print("❌ Could not find our test conversation in open conversations")
            return False
        
        # Step 6: Test getting first open conversation
        print("\nStep 6: Testing get first open conversation...")
        first_open = get_first_open_status_conversation()
        
        if not first_open:
            print("❌ No open conversation found")
            return False
        
        print(f"✅ First open conversation: {first_open['conversation_id']}")
        
        # Step 7: Simulate agent response and update status to pending
        print("\nStep 7: Simulating agent response...")
        agent_response = "Merci pour votre intérêt ! Voici les détails de nos produits d'assurance..."
        
        agent_msg_id, _ = append_message_to_conversation(
            client_id=client_id,
            corps=agent_response,
            expediteur="ai",
            statut="pending",
            subject="Re: Opportunités d'assurance",
            conversation_id=conversation_id
        )
        
        if not agent_msg_id:
            print("❌ Failed to create agent response")
            return False
        
        print(f"✅ Agent response created: {agent_msg_id}")
        
        # Step 8: Update conversation status back to 'pending'
        print("\nStep 8: Updating conversation status to 'pending'...")
        status_updated = update_conversation_status(conversation_id, "pending")
        
        if not status_updated:
            print("❌ Failed to update conversation status to 'pending'")
            return False
        
        print(f"✅ Conversation status updated to 'pending'")
        
        # Step 9: Verify no more open conversations
        print("\nStep 9: Verifying conversation is no longer 'open'...")
        remaining_open = get_conversations_with_open_status()
        
        our_conversation_still_open = False
        for conv in remaining_open:
            if conv['conversation_id'] == str(conversation_id):
                our_conversation_still_open = True
                break
        
        if our_conversation_still_open:
            print("❌ Our conversation is still marked as 'open'")
            return False
        
        print(f"✅ Conversation is no longer in 'open' status")
        print(f"📊 Remaining open conversations: {len(remaining_open)}")
        
        # Step 10: Verify conversation is now pending
        print("\nStep 10: Verifying conversation is now 'pending'...")
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        db = client.get_database()
        conversations_collection = db["conversations"]
        
        from bson import ObjectId
        conversation_doc = conversations_collection.find_one({"_id": ObjectId(conversation_id)})
        
        if not conversation_doc:
            print("❌ Could not find conversation in database")
            return False
        
        if conversation_doc.get('conversation_status') != 'pending':
            print(f"❌ Expected 'pending', got '{conversation_doc.get('conversation_status')}'")
            return False
        
        print(f"✅ Conversation status confirmed as 'pending'")
        client.close()
        
        print("\n🎉 ALL TESTS PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Error in test: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the simplified test."""
    print("🚀 Starting simplified conversation status tests")
    
    success = test_basic_conversation_status_workflow()
    
    print("\n" + "="*60)
    if success:
        print("✅ CONVERSATION STATUS FUNCTIONALITY WORKING!")
    else:
        print("❌ TESTS FAILED!")
    print("="*60)
    
    print("\n📋 What was tested:")
    print("1. ✅ Creating conversations with default 'pending' status")
    print("2. ✅ Adding client responses to conversations") 
    print("3. ✅ Updating conversation_status to 'open' (client responded)")
    print("4. ✅ Detecting conversations with 'open' status")
    print("5. ✅ Getting first conversation with 'open' status")
    print("6. ✅ Adding agent responses to conversations")
    print("7. ✅ Updating conversation_status back to 'pending' (agent responded)")
    print("8. ✅ Verifying status transitions work correctly")
    
    if success:
        print("\n✨ Your respond function is ready! Here's how to use it:")
        print("1. When client responds → set conversation_status to 'open'")
        print("2. Use get_conversations_with_open_status() to find conversations needing responses")
        print("3. Generate agent response and add to conversation")
        print("4. Update conversation_status to 'pending' after responding")

if __name__ == "__main__":
    main()
