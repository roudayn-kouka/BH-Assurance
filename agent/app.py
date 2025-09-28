from agent import SalesAgent, generate_initial_message, generate_response
from utils.mongodb_conn import get_conversations_with_open_status
from utils.general_utils import fetch_new_user_data
import time


def has_open_status_conversations() -> bool:
    """
    Check if there are conversations with 'open' status that need responses.
    Returns True if any exist, False otherwise.
    """
    open_conversations = get_conversations_with_open_status()
    return len(open_conversations) > 0


if __name__ == "__main__":
    agent = SalesAgent()
    print("🤖 BH Assurance AI Agent started!")
    print("🔍 Monitoring for conversations that need responses...")
    print("📋 Using new conversation status system:")
    print("   - 'open': Client responded, agent needs to generate response")
    print("   - 'pending': Agent responded, waiting for admin validation")
    print("-" * 60)
    
    try:
        while True:
            # Check for conversations with 'open' status (client responded)
            if has_open_status_conversations():
                print("📨 Found conversation(s) with 'open' status - generating responses...")
                reply, explanation = generate_response(agent)
                
                if reply:
                    print(
                        "=" * 60,
                        f"\n🤖 Agent Response Generated:",
                        f"\nResponse: {reply[:200]}{'...' if len(reply) > 200 else ''}",
                        f"\nExplanation: {explanation}",
                        f"\nStatus: Response saved as 'pending' - awaiting admin validation",
                        "\n" + "=" * 60,
                    )
                else:
                    print(f"❌ Failed to generate response: {explanation}")
            else:
                # No open conversations, try to get new user data for initial message
                user_data = fetch_new_user_data()
                if user_data:
                    print("👤 Processing new user data - generating initial message...")
                    reply, explanation, subject = generate_initial_message(agent, user_data)
                    print(
                        "=" * 60,
                        f"\n🚀 Initial Message Generated:",
                        f"\nSubject: {subject}",
                        f"\nMessage: {reply[:200]}{'...' if len(reply) > 200 else ''}",
                        f"\nExplanation: {explanation}",
                        f"\nStatus: Saved as 'pending' - awaiting admin validation",
                        "\n" + "=" * 60,
                    )
                else:
                    # No new data and no open conversations - wait a bit
                    print("✨ All conversations up to date - waiting for new activity...")
                    time.sleep(5)  # Wait 5 seconds before checking again

    except KeyboardInterrupt:
        print("\n🛑 Agent stopped by user.")
        print("👋 Thank you for using BH Assurance AI Agent!")
