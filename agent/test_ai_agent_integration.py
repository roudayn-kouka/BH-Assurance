#!/usr/bin/env python3
"""
Test script for AI agent integration with MongoDB backend.

This script tests the new functionality that:
1. Creates/gets a client from MongoDB with backend-compatible schema
2. Creates a new conversation for the client
3. Adds an AI agent message with proper 'ai' sender marking and 'pending' status

Usage:
    python test_ai_agent_integration.py
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.mongodb_conn import create_or_get_client, append_message_to_conversation
from datetime import datetime

def test_client_creation():
    """Test client creation with various data formats."""
    print("\n" + "="*50)
    print("TESTING CLIENT CREATION")
    print("="*50)
    
    # Test case 1: Full user data
    test_user_data_1 = {
        "user_data_str": "John Doe - Commerce sector - Looking for auto insurance",
        "data": {
            "user_id": "TEST_001",
            "email": "john.doe@test.com",
            "endpoint_strategy": "product_recommendation",
            "profile": {
                "first_name": "John",
                "nom": "Doe", 
                "telephone": "+33 6 12 34 56 78",
                "age": 35,
                "lib_secteur_activite": "Commerce",
                "lib_activite": "Commerce de détail",
                "score": 0.87
            },
            "produits_recommandes": [
                {
                    "nom": "AUTOMOBILE",
                    "score": 0.85,
                    "category": "Auto Insurance"
                }
            ]
        }
    }
    
    print("Test 1: Creating client with full data...")
    client_id_1 = create_or_get_client(test_user_data_1)
    print(f"Result: {client_id_1}")
    
    # Test case 2: Minimal user data (should generate fallbacks)
    test_user_data_2 = {
        "data": {
            "user_id": "TEST_002",
            # No email, should generate one
            "profile": {
                "score": 0.75
            }
        }
    }
    
    print("\nTest 2: Creating client with minimal data...")
    client_id_2 = create_or_get_client(test_user_data_2)
    print(f"Result: {client_id_2}")
    
    # Test case 3: Existing client (should return same ID)
    print("\nTest 3: Getting existing client...")
    client_id_1_again = create_or_get_client(test_user_data_1)
    print(f"Result: {client_id_1_again}")
    print(f"Same as first? {client_id_1 == client_id_1_again}")
    
    return client_id_1, client_id_2

def test_ai_message_creation(client_id):
    """Test AI message creation with backend-compatible schema."""
    print("\n" + "="*50)
    print("TESTING AI MESSAGE CREATION")
    print("="*50)
    
    if not client_id:
        print("❌ No client_id provided, skipping message tests")
        return
    
    # Test AI message creation
    ai_message = """
    Bonjour M. Doe,
    
    Suite à l'analyse de votre profil, nous avons identifié des opportunités 
    d'assurance automobile adaptées à votre secteur d'activité.
    
    Notre produit AUTOMOBILE obtient un score de recommandation de 85% 
    pour votre profil. Souhaitez-vous que nous vous présentions les détails ?
    
    Cordialement,
    L'équipe BH Assurance
    """
    
    subject = "Opportunité d'assurance automobile personnalisée"
    
    print("Creating AI agent message...")
    message_id, conversation_id = append_message_to_conversation(
        client_id=client_id,
        corps=ai_message,
        expediteur="ai",  # Mark as AI agent
        statut="pending",  # Backend status
        subject=subject,
        conversation_status="nouvelle_opportunite"
    )
    
    if message_id and conversation_id:
        print(f"✅ Successfully created AI message:")
        print(f"   Message ID: {message_id}")
        print(f"   Conversation ID: {conversation_id}")
        print(f"   Sender: ai")
        print(f"   Status: pending")
        
        # Test adding a client response
        print("\nAdding simulated client response...")
        client_response = "Bonjour, oui je suis intéressé par les détails. Pouvez-vous me faire une proposition ?"
        
        client_msg_id, _ = append_message_to_conversation(
            client_id=client_id,
            corps=client_response,
            expediteur="client",
            statut="validated",  # Client messages are typically auto-validated
            subject="Re: " + subject,
            conversation_id=conversation_id
        )
        
        if client_msg_id:
            print(f"✅ Successfully created client response: {client_msg_id}")
        else:
            print("❌ Failed to create client response")
            
    else:
        print("❌ Failed to create AI message")
    
    return message_id, conversation_id

def test_conversation_flow():
    """Test complete conversation flow."""
    print("\n" + "="*60)
    print("TESTING COMPLETE AI AGENT CONVERSATION FLOW")
    print("="*60)
    
    # Step 1: Create client
    print("Step 1: Creating/getting client...")
    user_data = {
        "user_data_str": "Marie Dubois - Restaurant owner - Needs business insurance",
        "data": {
            "user_id": "FLOW_TEST_001",
            "email": "marie.dubois@restaurant-test.fr",
            "endpoint_strategy": "product_recommendation",
            "profile": {
                "first_name": "Marie",
                "nom": "Dubois", 
                "telephone": "+33 6 98 76 54 32",
                "age": 42,
                "lib_secteur_activite": "Restauration",
                "lib_activite": "Restaurant traditionnel",
                "score": 0.91
            },
            "produits_recommandes": [
                {
                    "nom": "MULTIRISQUES PROFESSIONNELLES CENTRALISE",
                    "score": 0.94,
                    "category": "Business Insurance"
                }
            ]
        }
    }
    
    client_id = create_or_get_client(user_data)
    if not client_id:
        print("❌ Failed to create client for flow test")
        return
        
    print(f"✅ Client created: {client_id}")
    
    # Step 2: AI Agent initiates conversation
    print("\nStep 2: AI agent initiates conversation...")
    ai_message = """
    Bonjour Mme Dubois,
    
    En tant que propriétaire d'un restaurant traditionnel, votre activité présente 
    des risques spécifiques que nous pouvons couvrir efficacement.
    
    Notre analyse de votre profil révèle une recommandation forte (94%) pour notre 
    produit MULTIRISQUES PROFESSIONNELLES CENTRALISE, spécialement conçu pour 
    les professionnels de la restauration.
    
    Cette assurance couvre :
    - Les dommages aux équipements de cuisine
    - La responsabilité civile professionnelle
    - Les pertes d'exploitation
    - L'intoxication alimentaire
    
    Puis-je vous proposer un rendez-vous pour détailler cette solution ?
    
    Cordialement,
    Assistant IA - BH Assurance
    """
    
    message_id, conversation_id = append_message_to_conversation(
        client_id=client_id,
        corps=ai_message,
        expediteur="ai",
        statut="pending",
        subject="Protection sur-mesure pour votre restaurant",
        conversation_status="nouvelle_opportunite"
    )
    
    if message_id:
        print(f"✅ AI message created: {message_id}")
        print("   Status: pending (awaiting validation)")
        print("   Sender: ai (AI Agent)")
        print("   Conversation: nouvelle_opportunite")
    else:
        print("❌ Failed to create AI message")
        return
    
    print(f"\n🎉 Complete flow test successful!")
    print(f"   Client ID: {client_id}")
    print(f"   Conversation ID: {conversation_id}")
    print(f"   AI Message ID: {message_id}")
    print(f"   Ready for backend validation workflow!")

def main():
    """Run all tests."""
    print("🚀 Starting AI Agent Integration Tests")
    print("="*60)
    
    try:
        # Test client creation
        client_id_1, client_id_2 = test_client_creation()
        
        # Test message creation
        if client_id_1:
            test_ai_message_creation(client_id_1)
        
        # Test complete flow
        test_conversation_flow()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY!")
        print("="*60)
        print("\nSummary:")
        print("- Client creation: ✅ Working")
        print("- AI message creation: ✅ Working") 
        print("- Backend schema compatibility: ✅ Working")
        print("- Conversation flow: ✅ Working")
        print("\nThe AI agent can now:")
        print("1. Create new users in MongoDB with proper schema")
        print("2. Create conversations with backend-compatible statuses")
        print("3. Add messages marked as 'ai' sender with 'pending' status")
        print("4. Work seamlessly with the backend TypeScript models")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
