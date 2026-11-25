"""The LangChain product-recommendation scenario used for sales opportunities."""

from langchain_core.prompts import PromptTemplate

from config import PRODUCT_RECOMMENDATION_PROMPT


def product_recommendation_chain(model, template=PRODUCT_RECOMMENDATION_PROMPT):
    prompt = PromptTemplate.from_template(template)
    return prompt | model
