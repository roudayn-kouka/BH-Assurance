from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
import gc
from config import *
from transformers import AutoModelForCausalLM, AutoTokenizer

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
            .replace("{max_sentences}", str(MAX_SENTENCES)),
        )
        self.intitial_sales_prompt = PromptTemplate(
            input_variables=INITIAL_SALES_PROMPT_INPUT_VARS,
            template=INITIAL_SALES_PROMPT_TEMPLATE.replace(
                "{company_name}", COMPANY_NAME
            )
            .replace("{language}", LANGUAGE)
            .replace("{max_sentences}", str(MAX_SENTENCES)),
        )
        self.rag_prompt = PromptTemplate(
            input_variables=["conversation_history", "latest_user_message"],
            template=RAG_QUERY_PROMPT,
        )
        
        # -----------------------------
        # Scenario-Specific Prompts
        # -----------------------------
        self.product_recommendation_prompt = PromptTemplate(
            input_variables=["user_data", "rag_context", "product_name"],
            template=PRODUCT_RECOMMENDATION_PROMPT,
        )
        self.payment_reminder_prompt = PromptTemplate(
            input_variables=["user_data", "rag_context", "product_name"],
            template=PAYMENT_REMINDER_PROMPT,
        )
        self.contract_renewal_prompt = PromptTemplate(
            input_variables=["user_data", "rag_context", "product_name"],
            template=CONTRACT_RENEWAL_PROMPT,
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            LLM_SMALL_MODEL, torch_dtype="auto", device_map="auto"
        )
        self.tokenizer = AutoTokenizer.from_pretrained(LLM_SMALL_MODEL)
        # -----------------------------
        # Chains
        # -----------------------------
        self.sales_chain = self.sales_prompt | self.llm
        self.rag_chain = self.rag_prompt | self.llm
        self.initial_sales_chain = self.intitial_sales_prompt | self.llm
        
        # Scenario-specific chains
        self.product_recommendation_chain = self.product_recommendation_prompt | self.llm
        self.payment_reminder_chain = self.payment_reminder_prompt | self.llm
        self.contract_renewal_chain = self.contract_renewal_prompt | self.llm

    def generate_mail_object(self, mail_body):
        messages = [
            {
                "role": "system",
                "content": "Tu es un assistant qui génère uniquement l'objet d'un mail en français. "
                "Réponds par une seule ligne, maximum 8 mots. N'ajoute aucune explication.",
            },
            {
                "role": "user",
                "content": f"Contenu du mail :\n{mail_body}",
            },
        ]
        input_prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        model_inputs = self.tokenizer([input_prompt], return_tensors="pt").to(
            self.model.device
        )

        generated_ids = self.model.generate(
            **model_inputs,
            max_new_tokens=216,  # court, suffisant pour un objet
            do_sample=False,  # génération déterministe
            temperature=0.3,
        )
        generated_ids = [
            output_ids[len(input_ids) :]
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[
            0
        ]
        return response

    def query_llm(
        self,
        is_initial: bool,
        user_data,
        rag_context,
        product_name="",
        system_prompt="",
        user_message="",
        conversation_history="",
    ):
        """
        Query the sales LLM with provided data and conversation history.
        """
        if is_initial:
            response = self.initial_sales_chain.invoke(
                {
                    "user_data": user_data,
                    "rag_context": rag_context,
                    "product_name": product_name,
                }
            )
        else:
            response = self.sales_chain.invoke(
                {
                    "system_prompt": system_prompt,
                    "user_data": user_data,
                    "rag_context": rag_context,
                    "conversation_history": "\n".join(conversation_history),
                    "latest_user_message": user_message,
                }
            )
        return response

    def query_small_rag_llm(self, product_name):
        messages = [
            {
                "role": "system",
                "content": "Tu es un assistant qui produit uniquement des mots-clés/phrases pour une recherche vectorielle.",
            },
            {
                "role": "user",
                "content": SMALL_RAG_QUERY_PROMPT.replace(
                    "{product_name}", product_name
                ),
            },
        ]
        input_prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        model_inputs = self.tokenizer([input_prompt], return_tensors="pt").to(
            self.model.device
        )

        generated_ids = self.model.generate(**model_inputs, max_new_tokens=512)
        generated_ids = [
            output_ids[len(input_ids) :]
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]

        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[
            0
        ]
        return response

    def query_rag_llm(self, conversation_history, latest_user_message):
        """
        Query the RAG LLM with conversation context.
        """
        response = self.rag_chain.invoke(
            {
                "conversation_history": "\n".join(conversation_history),
                "latest_user_message": latest_user_message,
            }
        )
        return response
    
    def query_scenario_llm(self, scenario_type: str, user_data, rag_context, product_name):
        """
        Query the LLM using scenario-specific prompts.
        
        Args:
            scenario_type: One of 'product_recommendation', 'payment_reminder', 'contract_renewal'
            user_data: Formatted user data string
            rag_context: RAG context information
            product_name: Product name for the scenario
            
        Returns:
            LLM response using the appropriate scenario-specific prompt
        """
        scenario_chains = {
            "product_recommendation": self.product_recommendation_chain,
            "payment_reminder": self.payment_reminder_chain,
            "contract_renewal": self.contract_renewal_chain
        }
        
        if scenario_type not in scenario_chains:
            print(f"[LLM Warning] Unknown scenario type: {scenario_type}, falling back to default")
            return self.initial_sales_chain.invoke({
                "user_data": user_data,
                "rag_context": rag_context,
                "product_name": product_name,
            })
        
        chain = scenario_chains[scenario_type]
        response = chain.invoke({
            "user_data": user_data,
            "rag_context": rag_context,
            "product_name": product_name,
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
