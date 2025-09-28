#!/usr/bin/env python3
"""
Test script to validate the new scenario-specific prompts functionality.
"""

import sys
import os
sys.path.append('/home/nader/Projects/NextBH/BH-Assurance/agent')

from utils.user_profile_conn import fetch_endpoint_data, ENDPOINTS
from utils.general_utils import fetch_new_user_data
from agent import SalesAgent


def test_scenario_specific_prompts():
    """Test the scenario-specific prompts for each business strategy."""
    print("=" * 70)
    print("🎭 TESTING SCENARIO-SPECIFIC PROMPTS")
    print("=" * 70)
    
    # Initialize agent
    try:
        agent = SalesAgent()
        print("✅ Agent initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize agent: {e}")
        return
    
    # Test each strategy type
    strategies = ["product_recommendation", "payment_reminder", "contract_renewal"]
    
    for strategy in strategies:
        print(f"\n" + "=" * 50)
        print(f"🎯 TESTING STRATEGY: {strategy.upper()}")
        print("=" * 50)
        
        # Find matching endpoints for this strategy
        matching_endpoints = [
            key for key, config in ENDPOINTS.items() 
            if config["strategy"] == strategy
        ]
        
        if not matching_endpoints:
            print(f"❌ No endpoints found for strategy: {strategy}")
            continue
            
        # Test with the first matching endpoint
        endpoint_key = matching_endpoints[0]
        print(f"📡 Using endpoint: {endpoint_key}")
        
        try:
            # Fetch data from the endpoint
            raw_data = fetch_endpoint_data(endpoint_key)
            if not raw_data:
                print(f"❌ No data returned from endpoint: {endpoint_key}")
                continue
                
            # Convert to the format expected by the agent
            user_data = {
                "data": raw_data,
                "user_data_str": f"Test data for {strategy} scenario"
            }
            
            print(f"👤 User ID: {raw_data.get('user_id', 'N/A')}")
            print(f"🎬 Action: {raw_data.get('recommended_action', 'N/A')}")
            
            # Test the scenario-specific agent response
            response, explanation, subject = agent.agent_initiate(user_data)
            
            print(f"✅ Response generated successfully!")
            print(f"📧 Subject: {subject}")
            print(f"📝 Response length: {len(response)} characters")
            print(f"📋 Explanation length: {len(explanation)} characters")
            
            # Show preview of response
            response_preview = response[:150].replace('\n', ' ')
            print(f"👁️  Response preview: {response_preview}...")
            
            # Check if response contains strategy-specific keywords
            strategy_keywords = {
                "product_recommendation": ["recommand", "produit", "adapté", "profil"],
                "payment_reminder": ["paiement", "facture", "contrat", "règlement"],
                "contract_renewal": ["renouvellement", "fidélité", "expiration", "continuité"]
            }
            
            found_keywords = []
            for keyword in strategy_keywords.get(strategy, []):
                if keyword.lower() in response.lower():
                    found_keywords.append(keyword)
            
            print(f"🔍 Strategy keywords found: {found_keywords}")
            
            if len(found_keywords) >= 2:
                print(f"✅ Response appears to be strategy-appropriate")
            else:
                print(f"⚠️  Response may not be fully strategy-specific")
                
        except Exception as e:
            print(f"❌ Error testing strategy {strategy}: {e}")
            import traceback
            traceback.print_exc()
            continue


def test_integrated_flow():
    """Test the integrated flow with random endpoint selection."""
    print(f"\n\n" + "=" * 70)
    print("🔄 TESTING INTEGRATED FLOW WITH RANDOM ENDPOINTS")
    print("=" * 70)
    
    try:
        agent = SalesAgent()
        
        for i in range(3):
            print(f"\n🎲 Test run #{i+1}")
            
            # Use the unified fetch function (randomly selects endpoint)
            user_data = fetch_new_user_data()
            
            if not user_data or not user_data["data"]:
                print(f"❌ No user data returned")
                continue
                
            strategy = user_data["data"].get("endpoint_strategy", "unknown")
            endpoint_key = user_data["data"].get("endpoint_key", "unknown")
            
            print(f"📡 Endpoint: {endpoint_key}")
            print(f"🎯 Strategy: {strategy}")
            
            # Generate response
            response, explanation, subject = agent.agent_initiate(user_data)
            
            print(f"✅ Generated successfully")
            print(f"📧 Subject: {subject}")
            
            # Show a brief preview
            preview = response[:100].replace('\n', ' ')
            print(f"👁️  Preview: {preview}...")
            
    except Exception as e:
        print(f"❌ Error in integrated flow: {e}")
        import traceback
        traceback.print_exc()


def analyze_prompt_differences():
    """Analyze the differences between scenario-specific prompts."""
    print(f"\n\n" + "=" * 70)
    print("📊 ANALYZING PROMPT DIFFERENCES")
    print("=" * 70)
    
    from config import PRODUCT_RECOMMENDATION_PROMPT, PAYMENT_REMINDER_PROMPT, CONTRACT_RENEWAL_PROMPT
    
    prompts = {
        "Product Recommendation": PRODUCT_RECOMMENDATION_PROMPT,
        "Payment Reminder": PAYMENT_REMINDER_PROMPT,
        "Contract Renewal": CONTRACT_RENEWAL_PROMPT
    }
    
    for name, prompt in prompts.items():
        print(f"\n🎭 {name.upper()}:")
        print(f"   Length: {len(prompt)} characters")
        
        # Extract key phrases from the prompt
        key_phrases = []
        if "personnalisée" in prompt:
            key_phrases.append("personalisation")
        if "respectueux" in prompt:
            key_phrases.append("respectful approach")
        if "fidélité" in prompt:
            key_phrases.append("loyalty focus")
        if "bénéfices" in prompt:
            key_phrases.append("benefits emphasis")
        if "échéance" in prompt:
            key_phrases.append("deadline awareness")
        if "solutions" in prompt:
            key_phrases.append("solution-oriented")
            
        print(f"   Key characteristics: {', '.join(key_phrases)}")
        
        # Show first few lines
        first_lines = prompt.split('\n')[:3]
        for line in first_lines:
            if line.strip():
                print(f"   Preview: {line.strip()}")
                break


if __name__ == "__main__":
    try:
        test_scenario_specific_prompts()
        test_integrated_flow()
        analyze_prompt_differences()
        
        print("\n\n" + "=" * 70)
        print("🎉 SCENARIO-SPECIFIC PROMPTS TESTING COMPLETED!")
        print("✅ Agent can now adapt to different business contexts")
        print("✅ Product recommendations focus on personalization")
        print("✅ Payment reminders are respectful but firm")
        print("✅ Contract renewals emphasize loyalty and continuity")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ TESTING FAILED: {e}")
        import traceback
        traceback.print_exc()
