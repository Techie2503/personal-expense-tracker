"""
Gemini-based AI expense/income categorization.
Given a free-text description (and, for expenses, an optional receipt/
screenshot image), asks Gemini to pick the best-fit category from the
user's own live taxonomy (never invented) for each distinct expense or
income entry described - one input can describe a single entry or a list
of several (e.g. a shopping list, a multi-line receipt, or "got 5000
salary and 200 cashback") - extracting amount/date/merchant when present.
Runs a categorize -> reflect two-step pass: the second call is shown the
first call's own answer and asked to double-check it against the taxonomy.
"""
import os
import logging
from typing import Dict, List, Literal, Optional

from google import genai
from google.genai import types, errors
from pydantic import BaseModel

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")


class ExpenseSuggestion(BaseModel):
    c1_name: str
    c2_name: str
    confidence: float
    amount: Optional[float] = None
    date: Optional[str] = None
    merchant: Optional[str] = None
    notes: Optional[str] = None
    payment_mode: Optional[Literal["Cash", "Card", "UPI", "Net Banking"]] = None
    need_vs_want: Optional[Literal["Need", "Want", "Neutral"]] = None
    person: Optional[str] = None
    reasoning: str


class ExpenseSuggestionBatch(BaseModel):
    items: List[ExpenseSuggestion]


class IncomeSuggestion(BaseModel):
    category_name: str
    confidence: float
    amount: Optional[float] = None
    date: Optional[str] = None
    notes: Optional[str] = None
    reasoning: str


class IncomeSuggestionBatch(BaseModel):
    items: List[IncomeSuggestion]


class RateLimitedError(Exception):
    """Raised when the Gemini free-tier quota is exhausted (HTTP 429)."""


class GeminiService:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        self._client = genai.Client(api_key=api_key) if api_key else None
        if not self._client:
            logger.warning("GEMINI_API_KEY not set; AI categorization is disabled")

    def _taxonomy_text(self, taxonomy: Dict[str, List[str]]) -> str:
        return "\n".join(
            f"- {c1_name}: {', '.join(c2_names)}"
            for c1_name, c2_names in taxonomy.items()
        )

    def _call(self, parts: list, batch_cls: type) -> Optional[list]:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=batch_cls,
        )
        try:
            response = self._client.models.generate_content(
                model=GEMINI_MODEL,
                contents=parts,
                config=config,
            )
        except errors.ClientError as e:
            if e.code == 429:
                raise RateLimitedError(str(e)) from e
            logger.error(f"Gemini client error: {e}")
            return None
        except errors.ServerError as e:
            logger.error(f"Gemini server error: {e}")
            return None

        parsed = response.parsed
        return parsed.items if isinstance(parsed, batch_cls) else None

    def categorize_expenses(
        self,
        taxonomy: Dict[str, List[str]],
        text: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        image_mime_type: str = "image/jpeg",
    ) -> List[ExpenseSuggestion]:
        """
        taxonomy: {c1_name: [c2_name, ...]} for the current user only.
        Returns one ExpenseSuggestion per distinct expense found in the input
        - a single description/receipt returns a single-item list; a shopping
        list or a multi-line receipt returns one item per line.
        Raises RateLimitedError on Gemini quota exhaustion; returns [] on any
        other failure or unusable input, so callers always have a
        manual-categorization fallback.
        """
        if not self._client or (not text and not image_bytes):
            return []

        taxonomy_text = self._taxonomy_text(taxonomy)
        base_parts = [
            types.Part.from_text(text=(
                "You categorize personal expenses for a budgeting app. The "
                "input may describe a single expense, or several separate "
                "expenses (e.g. a shopping list like \"curd 15, milk 20, soap "
                "100\", or a receipt with multiple line items) - return one "
                "entry in `items` per distinct expense; a single expense "
                "still returns exactly one entry.\n"
                "For each entry, pick exactly one c1_name/c2_name pair from "
                "this user-defined list - never invent a category that isn't "
                "listed here. When more than one category could plausibly "
                "apply, prefer the most specific match over a generic/"
                "catch-all one - e.g. a personal-care item like soap or "
                "shampoo belongs in a bath/personal-care category if the "
                "list has one, not a generic household-items bucket:\n"
                f"{taxonomy_text}\n\n"
                "Also always classify need_vs_want as your best-judgment call "
                "of \"Need\", \"Want\", or \"Neutral\" for each expense - base "
                "it on the category and description, this field should never "
                "be left null.\n"
                "Only fill payment_mode (one of \"Cash\", \"Card\", \"UPI\", "
                "\"Net Banking\") if it is explicitly stated or visible (e.g. "
                "on a receipt) - leave it null if it's not mentioned, do not "
                "guess.\n"
                "Only fill person if the input explicitly names who the "
                "expense is for/with (e.g. \"for mom\", \"split with "
                "roommate\") - leave it null otherwise.\n"
                "Always fill notes with a short description of the item "
                "itself (e.g. \"curd\", \"coffee at Starbucks\") - derive it "
                "from the input text or receipt, this field should never be "
                "left null."
            ))
        ]
        if text:
            base_parts.append(types.Part.from_text(text=f"Expense description: {text}"))
        if image_bytes:
            base_parts.append(types.Part.from_bytes(data=image_bytes, mime_type=image_mime_type))
            base_parts.append(types.Part.from_text(text=(
                "The image is a receipt or payment screenshot, possibly with "
                "multiple line items. Extract the amount, date (ISO 8601 if "
                "determinable), merchant name, and payment mode if visible."
            )))

        step1 = self._call(base_parts + [
            types.Part.from_text(text="Return your best category picks now as JSON.")
        ], ExpenseSuggestionBatch)
        if not step1:
            return []

        step1_batch = ExpenseSuggestionBatch(items=step1)
        step2 = self._call(base_parts + [
            types.Part.from_text(text=(
                "Your first pass categorized these expense(s) as: "
                f"{step1_batch.model_dump_json()}\n"
                "Re-check each pick strictly against the allowed category "
                "list above. If any is a poor fit, an invented category, or a "
                "low-confidence guess, correct it. Return your final JSON answer "
                "with the same number of items."
            ))
        ], ExpenseSuggestionBatch)
        return step2 or step1

    def categorize_income(
        self,
        categories: List[str],
        text: Optional[str] = None,
    ) -> List[IncomeSuggestion]:
        """
        categories: flat list of the user's own live income category names
        (income categories have no C1/C2 hierarchy, unlike expenses).
        Returns one IncomeSuggestion per distinct income entry found in the
        input - e.g. "got 5000 salary and 200 cashback" returns two entries.
        Raises RateLimitedError on Gemini quota exhaustion; returns [] on any
        other failure or unusable input, so callers always have a
        manual-categorization fallback.
        """
        if not self._client or not text:
            return []

        categories_text = ", ".join(categories)
        base_parts = [
            types.Part.from_text(text=(
                "You categorize personal income/cash-inflow entries for a "
                "budgeting app. The input may describe a single inflow, or "
                "several separate ones (e.g. \"got 5000 salary and 200 "
                "cashback\") - return one entry in `items` per distinct "
                "inflow; a single inflow still returns exactly one entry.\n"
                "For each entry, pick exactly one category_name from this "
                "user-defined list - never invent a category that isn't "
                f"listed here: {categories_text}\n\n"
                "Extract the amount and date (ISO 8601 if determinable) for "
                "each entry from the text.\n"
                "Always fill notes with a short description of the entry "
                "itself (e.g. \"Salary\", \"Cashback from credit card\") - "
                "derive it from the input text, this field should never be "
                "left null."
            )),
            types.Part.from_text(text=f"Income description: {text}"),
        ]

        step1 = self._call(base_parts + [
            types.Part.from_text(text="Return your best category picks now as JSON.")
        ], IncomeSuggestionBatch)
        if not step1:
            return []

        step1_batch = IncomeSuggestionBatch(items=step1)
        step2 = self._call(base_parts + [
            types.Part.from_text(text=(
                "Your first pass categorized these income entries as: "
                f"{step1_batch.model_dump_json()}\n"
                "Re-check each pick strictly against the allowed category "
                "list above. If any is a poor fit or an invented category, "
                "correct it. Return your final JSON answer with the same "
                "number of items."
            ))
        ], IncomeSuggestionBatch)
        return step2 or step1


gemini_service = GeminiService()
