from agent import SalesAgent, generate_initial_message, generate_response
from utils.mongodb_conn import has_open_conversation
from utils.general_utils import fetch_new_user_data


if __name__ == "__main__":
    agent = SalesAgent()
    try:
        while True:

            # if has_open_conversation():
            #     reply = generate_response(agent)
            # else:
            user_data = fetch_new_user_data()
            reply, explanation, subject = generate_initial_message(agent, user_data)
            print(
                "=" * 50,
                f"\nAgent: \nobjet mail:{subject}\nCorps mail:\n{reply}\n",
                f"explanation: {explanation}",
                "=" * 50,
            )

    except KeyboardInterrupt:
        print("🛑 Conversation ended.")
