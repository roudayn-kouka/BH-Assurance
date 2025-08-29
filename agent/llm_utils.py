from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
import gc
from config import *

# -----------------------------
# LLM Setup
# -----------------------------

class LLM:
    def __init__(self):
        # Initialize the LLM
        self.llm = OllamaLLM(model=LLM_MODEL)

        # -----------------------------
        # Prompt Setup
        # -----------------------------
        self.sales_prompt = PromptTemplate(
            input_variables=SALES_PROMPT_INPUT_VARS,
            template=SALES_PROMPT_TEMPLATE.replace("{company_name}", COMPANY_NAME)
                                          .replace("{language}", LANGUAGE)
                                          .replace("{max_sentences}", str(MAX_SENTENCES))
        )
        self.rag_prompt = PromptTemplate(
            input_variables=["conversation_history", "latest_user_message"],
            template=RAG_QUERY_PROMPT
        )

        # -----------------------------
        # Chains
        # -----------------------------
        self.sales_chain = self.sales_prompt | self.llm
        self.rag_chain = self.rag_prompt | self.llm

    def query_llm(self, strategy, user_data, rag_context, user_message, conversation_history):
        """
        Query the sales LLM with provided data and conversation history.
        """
        response = self.sales_chain.invoke({
            "system_prompt": strategy["system_prompt"].format(company_name=COMPANY_NAME),
            "user_data": user_data,
            "rag_context": rag_context,
            "conversation_history": "\n".join(conversation_history),
            "latest_user_message": user_message,
        })
        return response

    def query_rag_llm(self, conversation_history, latest_user_message):
        """
        Query the RAG LLM with conversation context.
        """
        response = self.rag_chain.invoke({
            "conversation_history": "\n".join(conversation_history),
            "latest_user_message": latest_user_message,
        })
        return response
    def destroy(self):
        """
        Clean up memory and internal cache.
        """
        try:
            del self.sales_chain
            del self.rag_chain
            del self.sales_prompt
            del self.rag_prompt
            del self.llm
        except Exception as e:
            print(f"⚠️ Warning during destroy: {e}")
        finally:
            gc.collect()
            print("🧹 LLM resources cleaned and memory freed.")