from agent import SalesAgent, generate_initial_message, generate_response
from mongodb_conn import has_open_conversation
from utils import fetch_new_user_data


if __name__ == "__main__":
    agent = SalesAgent()
    client_id = "64f123456789abcdef123456"  # replace with real client _id from DB

    try:
        while True:

            if has_open_conversation():
                reply = generate_response(agent)
            else:
                user_data = fetch_new_user_data()
                reply = generate_initial_message(agent, user_data)
            print(f"Agent: {reply}\n")

    except KeyboardInterrupt:
        print("🛑 Conversation ended.")
