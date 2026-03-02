"""LLM-backed guidelines lookup service for council recycling advice.

Fetches the relevant recyclingnearyou.com.au page as grounding context,
calls OpenAI to extract a structured bin decision, and caches results
in-memory for 1 week (TTL from settings).
"""

import json
import logging
import pathlib
import time
from dataclasses import dataclass, replace

import httpx
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

RNY_MATERIAL_BASE = "https://recyclingnearyou.com.au/material/home"
RNY_COUNCIL_BASE = "https://recyclingnearyou.com.au/council"
SCRAPE_HEADERS = {
    "User-Agent": "recycling-buddy/0.1 (educational use; contact: admin@recyclingbuddy.com.au)"
}
FETCH_TIMEOUT = 10.0  # seconds


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
You are a recycling advisor for Australian households. You will be given the HTML content \
of a recyclingnearyou.com.au page and asked to extract the recycling advice for a specific \
item in a specific council area.

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
- If you cannot find specific advice for the item in the provided page content, \
  set is_fallback to true and use red bin / General Waste as the safe default
- Never invent council-specific rules not present in the page content
- Respond with valid JSON only, no markdown fences
"""


class GuidelinesService:
    """Provides LLM-backed bin advice for (item_category, council_slug) pairs.

    On each lookup:
    1. Check in-memory cache (TTL = settings.guidelines_cache_ttl_seconds)
    2. Fetch the RNY item page for the council as grounding context
    3. Call OpenAI with the page HTML and extract a structured AdviceRecord
    4. If fetch or LLM fails, fall back to general waste + disclaimer
    5. Cache and return the result
    """

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str], tuple[AdviceRecord, float]] = {}
        self._ttl = settings.guidelines_cache_ttl_seconds
        self._openai = (
            AsyncOpenAI(api_key=settings.openai_api_key)
            if settings.openai_api_key
            else None
        )
        self._label_to_rny: dict[str, dict] = self._load_mapping()

    def _load_mapping(self) -> dict[str, dict]:
        """Load the label-to-RNY slug mapping table.

        Returns:
            Dict mapping classifier label strings to RNY entry dicts
            containing rny_slug, rny_url, and notes fields.
        """
        path = pathlib.Path(settings.guidelines_data_path)
        if not path.exists():
            logger.warning(
                "label_to_rny.json not found at %s — all lookups will use training data only",
                path,
            )
            return {}
        return json.loads(path.read_text())

    def _rny_url(self, item_category: str, council_slug: str) -> str | None:
        """Construct the RNY item+council URL for grounding, or None if unmapped.

        Args:
            item_category: Classifier label (e.g. 'cardboard').
            council_slug: RNY council slug (e.g. 'SydneyNSW').

        Returns:
            Full RNY URL string scoped to the council, or None if no slug available.
        """
        entry = self._label_to_rny.get(item_category)
        if not entry or not entry.get("rny_slug"):
            return None
        slug = entry["rny_slug"]
        # Try the item page scoped to the council for more specific advice
        return f"{RNY_MATERIAL_BASE}/{slug}/{council_slug}"

    async def _fetch_page(self, url: str) -> str | None:
        """Fetch a URL and return the text content, or None on failure.

        Args:
            url: The URL to fetch.

        Returns:
            Response text on success, None on HTTP error or network failure.
        """
        try:
            async with httpx.AsyncClient(
                headers=SCRAPE_HEADERS, timeout=FETCH_TIMEOUT
            ) as client:
                resp = await client.get(url, follow_redirects=True)
                if resp.status_code == 200:
                    return resp.text
                logger.warning("RNY fetch returned %d for %s", resp.status_code, url)
                return None
        except Exception as exc:
            logger.warning("RNY fetch failed for %s: %s", url, exc)
            return None

    async def _call_llm(
        self,
        item_category: str,
        council_slug: str,
        page_html: str | None,
    ) -> AdviceRecord:
        """Call OpenAI to extract advice, falling back to general waste if unavailable.

        Args:
            item_category: Classifier label (e.g. 'cardboard').
            council_slug: RNY council slug (e.g. 'SydneyNSW').
            page_html: HTML content from RNY page, or None if page fetch failed.

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

        if page_html:
            # Truncate HTML to ~8000 chars to stay within context budget for gpt-4o-mini
            context_block = page_html[:8000]
            user_message = (
                f"Council: {council_slug}\n"
                f"Item: {item_category}\n\n"
                f"Page content from recyclingnearyou.com.au:\n{context_block}\n\n"
                "Extract the recycling advice for this item in this council area."
            )
        else:
            # No grounding — LLM answers from training data alone
            user_message = (
                f"Council: {council_slug}\n"
                f"Item: {item_category}\n\n"
                "The recyclingnearyou.com.au page was unavailable. "
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

        Checks cache first. On miss: fetches RNY page as grounding context,
        calls OpenAI, caches and returns result. Falls back to general waste
        on any failure.

        Args:
            item_category: Classifier label (e.g. 'cardboard', 'glass-bottles-jars').
            council_slug: RNY council slug (e.g. 'SydneyNSW', 'MelbourneVIC').

        Returns:
            AdviceRecord with is_fallback=False on success, True on fallback.
        """
        cache_key = (item_category, council_slug)
        cached = self._cache.get(cache_key)
        if cached:
            record, inserted_at = cached
            if time.time() - inserted_at < self._ttl:
                logger.info("Cache hit for %s/%s", item_category, council_slug)
                return record
            del self._cache[cache_key]

        url = self._rny_url(item_category, council_slug)
        page_html = await self._fetch_page(url) if url else None

        record = await self._call_llm(item_category, council_slug, page_html)
        self._cache[cache_key] = (record, time.time())
        logger.info(
            "Guidelines lookup: item=%s council=%s fallback=%s",
            item_category,
            council_slug,
            record.is_fallback,
        )
        return record
