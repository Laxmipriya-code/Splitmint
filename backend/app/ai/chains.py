from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

from app.core.config import Settings
from app.schemas.ai import MintSenseExpenseDraft, MintSenseGroupSummaryRead


class LangChainMintSenseClient:
    def __init__(self, settings: Settings):
        from langchain_openai import ChatOpenAI

        self._expense_model = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0,
        ).with_structured_output(MintSenseExpenseDraft)
        self._summary_model = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0,
        ).with_structured_output(MintSenseGroupSummaryRead)

    def parse_expense(self, text: str, participant_names: list[str]) -> MintSenseExpenseDraft:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are MintSense, a conservative expense parser. "
                    "Return only data that is grounded in the input. "
                    "If anything is unclear, set needs_confirmation=true and explain ambiguities.",
                ),
                (
                    "human",
                    "Known participant names: {participant_names}\nExpense text: {text}",
                ),
            ]
        )
        return self._expense_model.invoke(
            prompt.format_messages(
                text=text,
                participant_names=", ".join(participant_names)
                if participant_names
                else "none provided",
            )
        )

    def summarize_group(self, context: dict[str, object]) -> MintSenseGroupSummaryRead:
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You summarize group expense ledgers in plain language. "
                    "Do not invent amounts. Use the provided facts only.",
                ),
                ("human", "Ledger context: {context}"),
            ]
        )
        return self._summary_model.invoke(prompt.format_messages(context=context))
