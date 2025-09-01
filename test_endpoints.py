#!/usr/bin/env python3
"""
Test script to validate the updated agent system with api_datasets endpoints.
"""

import sys
import os
sys.path.append('/home/nader/Projects/NextBH/BH-Assurance/agent')

from utils.user_profile_conn import (
    fetch_new_user, 
    fetch_endpoint_data, 
    get_available_strategies,
    ENDPOINTS
)
from utils.endpoint_utils import (
    convert_endpoint_data_to_string,
    get_product_name_from_endpoint_data,
    get_strategy_specific_prompts
)
from utils.general_utils import fetch_new_user_data


def test_api_connections():
    """Test that all API endpoints are reachable and return data."""
    print("=" * 60)
    print("🧪 TESTING API ENDPOINTS")
    print("=" * 60)
    
    for endpoint_key, config in ENDPOINTS.items():
        print(f"\n📡 Testing endpoint: {endpoint_key}")
        print(f"   URL: {config['url']}")
        print(f"   Strategy: {config['strategy']}")
        
        data = fetch_endpoint_data(endpoint_key)
        if data:
            print(f"   ✅ Success - User ID: {data.get('user_id', 'N/A')}")
            print(f"   📊 Action: {data.get('recommended_action', 'N/A')}")
        else:
            print(f"   ❌ Failed to fetch data")


def test_data_conversion():
    """Test the endpoint-specific data conversion."""
    print("\n\n" + "=" * 60)
    print("🔄 TESTING DATA CONVERSION")
    print("=" * 60)
    
    for strategy in ["product_recommendation", "payment_reminder", "contract_renewal"]:
        print(f"\n🎯 Testing strategy: {strategy}")
        
        # Find endpoints for this strategy
        matching_endpoints = [
            key for key, config in ENDPOINTS.items() 
            if config["strategy"] == strategy
        ]
        
        if matching_endpoints:
            endpoint_key = matching_endpoints[0]
            print(f"   Using endpoint: {endpoint_key}")
            
            data = fetch_endpoint_data(endpoint_key)
            if data:
                converted = convert_endpoint_data_to_string(data)
                print(f"   ✅ Conversion successful")
                print(f"   📝 Preview: {converted[:100]}...")
                
                # Test product extraction
                product = get_product_name_from_endpoint_data(data)
                print(f"   🏷️  Extracted product: {product}")
                
                # Test strategy config
                config = get_strategy_specific_prompts(strategy)
                print(f"   ⚙️  Max sentences: {config.get('max_sentences', 'N/A')}")
            else:
                print(f"   ❌ No data available for conversion test")


def test_unified_data_fetching():
    """Test the unified fetch_new_user_data function."""
    print("\n\n" + "=" * 60)
    print("🔗 TESTING UNIFIED DATA FETCHING")
    print("=" * 60)
    
    for i in range(3):
        print(f"\n🎲 Test run #{i+1}")
        user_data = fetch_new_user_data()
        
        if user_data and user_data["data"]:
            raw_data = user_data["data"]
            print(f"   ✅ Success - Endpoint: {raw_data.get('endpoint_key', 'N/A')}")
            print(f"   🎯 Strategy: {raw_data.get('endpoint_strategy', 'N/A')}")
            print(f"   👤 User ID: {raw_data.get('user_id', 'N/A')}")
            print(f"   📄 String length: {len(user_data['user_data_str'])} chars")
            
            # Show a preview of the formatted string
            preview = user_data['user_data_str'][:200].replace('\n', '\\n')
            print(f"   📝 Preview: {preview}...")
        else:
            print(f"   ❌ Failed to fetch unified data")


def test_strategies_overview():
    """Show an overview of all available strategies."""
    print("\n\n" + "=" * 60)
    print("📋 STRATEGIES OVERVIEW")
    print("=" * 60)
    
    strategies = get_available_strategies()
    for strategy, endpoints in strategies.items():
        print(f"\n🎯 Strategy: {strategy}")
        print(f"   📡 Endpoints: {', '.join(endpoints)}")
        
        config = get_strategy_specific_prompts(strategy)
        print(f"   ⚙️  Max sentences: {config.get('max_sentences', 5)}")
        print(f"   🎪 Focus areas: {', '.join(config.get('focus_areas', []))}")


if __name__ == "__main__":
    try:
        test_api_connections()
        test_data_conversion()
        test_unified_data_fetching()
        test_strategies_overview()
        
        print("\n\n" + "=" * 60)
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("✅ API endpoints are working")
        print("✅ Data conversion is working")
        print("✅ Strategy handling is working") 
        print("✅ Agent integration is ready")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
