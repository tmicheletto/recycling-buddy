"""LLM-backed guidelines lookup service for council recycling advice.

Uses Tavily search to find relevant recyclingnearyou.com.au pages as
grounding context, calls OpenAI to extract a structured bin decision,
and caches results in-memory (advice: 1 week TTL, search: 24h TTL).
"""

import json
import logging
import time
from dataclasses import dataclass, replace

from openai import AsyncOpenAI
from tavily import TavilyClient

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AdviceRecord:
    """Structured bin advice for a single (item_category, council_slug) pair."""

    bin_colour: str  # "red" | "yellow" | "green" | "blue" | "purple" | "special"
    bin_name: str  # e.g. "General Waste", "Recycling"
    prep_instructions: str  # e.g. "Rinse, remove lid, flatten" or ""
    disposal_method: str  # "kerbside" | "special_disposal" | "drop_off"
    special_disposal_flag: bool
    notes: str
    is_fallback: bool
    council_slug: str
    item_category: str


_FALLBACK = AdviceRecord(
    bin_colour="red",
    bin_name="General Waste",
    prep_instructions="",
    disposal_method="kerbside",
    special_disposal_flag=False,
    notes=(
        "We couldn't find specific advice for this item — "
        "general waste is the safe choice to prevent recycling contamination. "
        "Check your council's website for more information."
    ),
    is_fallback=True,
    council_slug="",
    item_category="",
)


SYSTEM_PROMPT = """\
You are a recycling advisor for Australian households. You will be given search \
results from recyclingnearyou.com.au and asked to extract the recycling advice for \
a specific item in a specific council area.

Respond ONLY with a JSON object matching this exact schema:
{
  "bin_colour": "<red|yellow|green|blue|purple|special>",
  "bin_name": "<bin display name, e.g. General Waste, Recycling, FOGO>",
  "prep_instructions": "<prep steps or empty string>",
  "disposal_method": "<kerbside|special_disposal|drop_off>",
  "special_disposal_flag": <true|false>,
  "notes": "<any extra context or empty string>",
  "is_fallback": <true|false>
}

Rules:
- bin_colour must be one of: red, yellow, green, blue, purple, special
- If the item requires special disposal (e.g. batteries, e-waste, chemicals), set \
  disposal_method to "special_disposal" and special_disposal_flag to true
- If you cannot find specific advice for the item in the provided search results, \
  set is_fallback to true and use red bin / General Waste as the safe default
- Never invent council-specific rules not present in the search results
- Respond with valid JSON only, no markdown fences
"""


class GuidelinesService:
    """Provides LLM-backed bin advice for (item_category, council_slug) pairs.

    On each lookup:
    1. Check in-memory advice cache (TTL = settings.guidelines_cache_ttl_seconds)
    2. Check in-memory search cache (TTL = settings.search_cache_ttl_seconds)
    3. On search miss: call Tavily to search recyclingnearyou.com.au
    4. Call OpenAI with the search content and extract a structured AdviceRecord
    5. If search or LLM fails, fall back to general waste + disclaimer
    6. Cache and return the result
    """

    def __init__(self) -> None:
        self._advice_cache: dict[tuple[str, str], tuple[AdviceRecord, float]] = {}
        self._search_cache: dict[tuple[str, str], tuple[str, float]] = {}
        self._advice_ttl = settings.guidelines_cache_ttl_seconds
        self._search_ttl = settings.search_cache_ttl_seconds
        self._openai = (
            AsyncOpenAI(api_key=settings.openai_api_key)
            if settings.openai_api_key
            else None
        )
        self._tavily = (
            TavilyClient(api_key=settings.tavily_api_key)
            if settings.tavily_api_key
            else None
        )

    def _search_rny(self, item_category: str, council_slug: str) -> str | None:
        """Search recyclingnearyou.com.au for item + council recycling advice.

        Args:
            item_category: Classifier label (e.g. 'cardboard').
            council_slug: RNY council slug (e.g. 'SydneyNSW').

        Returns:
            Extracted text content from search results, or None if no results.
        """
        if not self._tavily:
            return None

        # Check search cache
        cache_key = (item_category, council_slug)
        cached = self._search_cache.get(cache_key)
        if cached:
            content, inserted_at = cached
            if time.time() - inserted_at < self._search_ttl:
                logger.info("Search cache hit for %s/%s", item_category, council_slug)
                return content
            del self._search_cache[cache_key]

        # Human-readable query for Tavily
        query = f"{item_category.replace('-', ' ')} recycling {council_slug}"
        try:
            response = self._tavily.search(
                query=query,
                search_depth="basic",
                include_domains=["recyclingnearyou.com.au"],
                max_results=3,
            )
            results = response.get("results", [])
            if not results:
                logger.info(
                    "Tavily returned no results for %s/%s",
                    item_category,
                    council_slug,
                )
                return None

            # Concatenate extracted content from top results
            content = "\n\n---\n\n".join(
                f"Source: {r.get('url', 'unknown')}\n{r.get('content', '')}"
                for r in results
            )
            self._search_cache[cache_key] = (content, time.time())
            return content

        except Exception as exc:
            logger.warning(
                "Tavily search failed for %s/%s: %s",
                item_category,
                council_slug,
                exc,
            )
            return None

    async def _call_llm(
        self,
        item_category: str,
        council_slug: str,
        search_content: str | None,
    ) -> AdviceRecord:
        """Call OpenAI to extract advice, falling back to general waste if unavailable.

        Args:
            item_category: Classifier label (e.g. 'cardboard').
            council_slug: RNY council slug (e.g. 'SydneyNSW').
            search_content: Extracted text from Tavily search, or None.

        Returns:
            AdviceRecord from LLM extraction, or fallback record on failure.
        """
        if not self._openai:
            logger.warning(
                "No OPENAI_API_KEY configured — returning fallback for %s/%s",
                item_category,
                council_slug,
            )
            return replace(
                _FALLBACK, council_slug=council_slug, item_category=item_category
            )

        if search_content:
            context_block = search_content[:8000]
            user_message = (
                f"Council: {council_slug}\n"
                f"Item: {item_category}\n\n"
                f"Search results from recyclingnearyou.com.au:\n{context_block}\n\n"
                "Extract the recycling advice for this item in this council area."
            )
        else:
            user_message = (
                f"Council: {council_slug}\n"
                f"Item: {item_category}\n\n"
                "No search results were available from recyclingnearyou.com.au. "
                "Using your training knowledge, provide the most likely recycling advice "
                "for this item in an Australian council context. "
                "If uncertain, set is_fallback to true."
            )

        try:
            response = await self._openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            raw = response.choices[0].message.content or "{}"
            data = json.loads(raw)
            return AdviceRecord(
                bin_colour=data.get("bin_colour", "red"),
                bin_name=data.get("bin_name", "General Waste"),
                prep_instructions=data.get("prep_instructions", ""),
                disposal_method=data.get("disposal_method", "kerbside"),
                special_disposal_flag=bool(data.get("special_disposal_flag", False)),
                notes=data.get("notes", ""),
                is_fallback=bool(data.get("is_fallback", False)),
                council_slug=council_slug,
                item_category=item_category,
            )
        except Exception as exc:
            logger.error(
                "OpenAI call failed for %s/%s: %s", item_category, council_slug, exc
            )
            return replace(
                _FALLBACK, council_slug=council_slug, item_category=item_category
            )

    async def lookup(self, item_category: str, council_slug: str) -> AdviceRecord:
        """Return bin advice for (item_category, council_slug).

        Checks advice cache first. On miss: searches RNY via Tavily for grounding
        context, calls OpenAI, caches and returns result. Falls back to general
        waste on any failure.

        Args:
            item_category: Classifier label (e.g. 'cardboard', 'glass-bottles-jars').
            council_slug: RNY council slug (e.g. 'SydneyNSW', 'MelbourneVIC').

        Returns:
            AdviceRecord with is_fallback=False on success, True on fallback.
        """
        cache_key = (item_category, council_slug)

        # Tier 1: advice cache
        cached = self._advice_cache.get(cache_key)
        if cached:
            record, inserted_at = cached
            if time.time() - inserted_at < self._advice_ttl:
                logger.info("Advice cache hit for %s/%s", item_category, council_slug)
                return record
            del self._advice_cache[cache_key]

        # Tier 2: search cache (or fresh Tavily call)
        search_content = self._search_rny(item_category, council_slug)

        record = await self._call_llm(item_category, council_slug, search_content)
        self._advice_cache[cache_key] = (record, time.time())
        logger.info(
            "Guidelines lookup: item=%s council=%s fallback=%s",
            item_category,
            council_slug,
            record.is_fallback,
        )
        return record
