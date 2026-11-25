from agent import SalesAgent, generate_initial_message, generate_response
from utils.mongodb_conn import get_conversations_with_open_status
from utils.general_utils import fetch_new_user_data
import argparse
import time


def has_open_status_conversations() -> bool:
    """
    Check if there are conversations with 'open' status that need responses.
    Returns True if any exist, False otherwise.
    """
    open_conversations = get_conversations_with_open_status()
    return len(open_conversations) > 0


def run_cycle(agent: SalesAgent) -> bool:
    """Handle one open conversation or one new prospect. Return False when idle."""
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
        return True

    # No open conversations, try to get new user data for initial message.
    # fetch_new_user_data() always returns a dict; "data" is None when the API had nothing.
    user_data = fetch_new_user_data()
    if not user_data or not user_data.get("data"):
        return False

    print("👤 Processing new user data - generating initial message...")
    reply, explanation, subject = generate_initial_message(agent, user_data)
    if reply is None:
        print(f"⏸️  Initial contact deferred by policy:\n{explanation}")
        return True
    print(
        "=" * 60,
        f"\n🚀 Initial Message Generated:",
        f"\nSubject: {subject}",
        f"\nMessage: {reply[:200]}{'...' if len(reply) > 200 else ''}",
        f"\nExplanation: {explanation}",
        f"\nStatus: Saved as 'pending' - awaiting admin validation",
        "\n" + "=" * 60,
    )
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BH Assurance sales agent")
    parser.add_argument("--once", action="store_true",
                        help="handle a single conversation or prospect, then exit")
    args = parser.parse_args()

    agent = SalesAgent()
    print("🤖 BH Assurance AI Agent started!")
    print("🔍 Monitoring for conversations that need responses...")
    print("📋 Using new conversation status system:")
    print("   - 'open': Client responded, agent needs to generate response")
    print("   - 'pending': Agent responded, waiting for admin validation")
    print("-" * 60)

    try:
        while True:
            worked = run_cycle(agent)
            if args.once:
                break
            if not worked:
                # No new data and no open conversations - wait a bit
                print("✨ All conversations up to date - waiting for new activity...")
                time.sleep(5)  # Wait 5 seconds before checking again

    except KeyboardInterrupt:
        print("\n🛑 Agent stopped by user.")
        print("👋 Thank you for using BH Assurance AI Agent!")
