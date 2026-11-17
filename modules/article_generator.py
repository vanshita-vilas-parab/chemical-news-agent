
import os
import json
import time
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types

from modules.style_guide import get_style_guide

load_dotenv()


# --------------------------------------------------
# 1. INPUT CLEANING
# --------------------------------------------------

def clean_list(items):
    """Return a clean list without empty entries."""
    cleaned = []

    for item in items or []:
        if isinstance(item, dict):
            item = (
                item.get("description")
                or item.get("value")
                or item.get("text")
                or ""
            )

        if isinstance(item, str) and item.strip():
            cleaned.append(item.strip())

    return cleaned


def format_facts(facts):
    """Format all extracted facts without silently dropping details."""
    return "\n".join(
        f"[FACT {index}] {fact}"
        for index, fact in enumerate(clean_list(facts), 1)
    )


def parse_json_response(response_text):
    """Parse JSON while handling optional Markdown code fences."""
    if not response_text:
        raise ValueError("Empty response from Gemini.")

    cleaned = response_text.strip()

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    cleaned = re.sub(r"\s*```$", "", cleaned)

    result = json.loads(cleaned)

    if not isinstance(result, dict):
        raise ValueError("Gemini returned an invalid JSON object.")

    return result


# --------------------------------------------------
# 2. GEMINI CLIENT
# --------------------------------------------------

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing.")

    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                attempts=2,
                initial_delay=2,
                max_delay=6,
                exp_base=2,
                jitter=0.2
            )
        )
    )


def get_model():
    return os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


# --------------------------------------------------
# 3. ARTICLE GENERATION PROMPT
# --------------------------------------------------

def create_prompt(
    news,
    extracted_facts,
    business_implications=None,
    editorial_analysis=None
):
    """Create a source-grounded ChemStride article prompt."""

    style = get_style_guide()

    facts = clean_list(extracted_facts)
    implications = clean_list(business_implications)
    analysis = clean_list(editorial_analysis)

    if not facts:
        raise ValueError("No extracted facts are available.")

    facts_text = format_facts(facts)

    implications_text = "\n".join(
        f"- {item}" for item in implications
    ) or "No source-supported business implications supplied."

    analysis_text = "\n".join(
        f"- {item}" for item in analysis
    ) or "No editorial analysis supplied."

    title = news.get("title", "Chemical Industry Update")
    publisher = news.get("source") or news.get("publisher", "Not provided")
    published = news.get("published", "Not provided")

    source_url = (
        news.get("original_url")
        or news.get("link")
        or news.get("url")
        or "Not provided"
    )

    return f"""
You are writing a professional LinkedIn industry article
for ChemStride.

Follow these writing guidelines:

{style}

SOURCE INFORMATION

Headline: {title}
Publisher: {publisher}
Published: {published}
Original article: {source_url}

SOURCE-EXTRACTED FACTS

{facts_text}

SOURCE-SUPPORTED BUSINESS IMPLICATIONS

{implications_text}

EDITORIAL ANALYSIS

{analysis_text}


ARTICLE OBJECTIVE

Create a clear, informative and engaging LinkedIn article
based on the supplied source information.

CONTENT REQUIREMENTS

1. Start with a strong, accurate headline.
2. Explain the actual development clearly.
3. Include all materially important supplied facts.
4. Preserve important figures, dates, names, locations
   and project details accurately.
5. Explain the development in a logical sequence.
6. Use short paragraphs and meaningful headings.
7. Include business implications only when supplied.
8. Clearly distinguish editorial analysis from reported facts.
9. End with a relevant industry question or takeaway.
10. Add 4-6 relevant hashtags.
11. Use natural, professional English.
12. Follow ChemStride's writing style.
13. Avoid repetition and generic filler.

STRICT FACTUAL RULES

- Treat SOURCE-EXTRACTED FACTS as the factual evidence.
- Do not introduce external knowledge or assumptions.
- Do not invent statistics, dates, quotations or statements.
- Do not change company names, locations or figures.
- Preserve the exact meaning of financial amounts.
- Do not convert plans, proposals or announcements
  into completed activities.
- Preserve distinctions between planned, ongoing
  and completed developments.
- Do not claim that a facility is operational unless
  the supplied facts establish that.
- Do not present possible market effects as confirmed results.
- Do not invent customer demand, production volumes,
  revenue, employment or financial effects.
- Do not add unsupported comparisons with other companies.
- Do not claim independent verification.
- If a detail is unavailable, leave it out.
- Do not repeat a fact merely to increase word count.
- Do not force the article to reach a particular length.
- Do not omit an important supplied fact just to make
  the article shorter.

IMPORTANT

The article should be a well-written industry report,
not a fictional expansion of the original news.

Use editorial analysis only as clearly labelled interpretation.
Do not disguise interpretation as a reported fact.

Return only the complete LinkedIn article in Markdown.
"""


# --------------------------------------------------
# 4. ARTICLE CLAIM VERIFICATION
# --------------------------------------------------

def create_verification_prompt(
    news,
    extracted_facts,
    business_implications,
    editorial_analysis,
    article
):
    """
    Ask Gemini to compare every factual claim in the article
    with the supplied source-backed information.
    """

    facts_text = format_facts(extracted_facts)

    implications_text = "\n".join(
        f"- {item}"
        for item in clean_list(business_implications)
    ) or "None supplied."

    analysis_text = "\n".join(
        f"- {item}"
        for item in clean_list(editorial_analysis)
    ) or "None supplied."

    return f"""
You are a strict factual editor reviewing a LinkedIn article
for ChemStride.

Your task is to identify unsupported factual claims.

SOURCE HEADLINE:
{news.get("title", "")}

SOURCE-EXTRACTED FACTS:
{facts_text}

SOURCE-SUPPORTED BUSINESS IMPLICATIONS:
{implications_text}

EDITORIAL ANALYSIS:
{analysis_text}

GENERATED ARTICLE:
{article}

VERIFICATION RULES:

1. Check every factual statement against the supplied facts.
2. Check all company names, dates, amounts, figures,
   locations and project details.
3. Check whether plans are incorrectly described
   as completed activities.
4. Check whether the article changes the meaning
   or certainty of the original development.
5. Check whether business implications are presented
   as confirmed outcomes without evidence.
6. Editorial interpretation is allowed only when clearly
   presented as analysis, not as a confirmed fact.
7. Generic questions and calls to action are acceptable.
8. Hashtags do not need factual verification.
9. Do not use outside knowledge to approve a claim.
10. If a claim cannot be supported, remove or rewrite it.
11. Do not introduce new factual claims while correcting.
12. Preserve all important supported information.

Return JSON only, using this exact structure:

{{
    "approved": true,
    "unsupported_claims": [],
    "corrected_article": "Complete corrected article in Markdown",
    "review_notes": "Brief explanation of the review"
}}

Set approved to true only if the corrected article
contains no unsupported factual claims.

If you cannot establish that the article is supported
by the supplied information, set approved to false.

The corrected article must not introduce new facts.
"""


def verify_generated_article(
    client,
    news,
    extracted_facts,
    business_implications,
    editorial_analysis,
    article
):
    """
    Review the generated article against supplied facts.

    Returns a corrected article only when the review
    explicitly approves it.
    """

    prompt = create_verification_prompt(
        news,
        extracted_facts,
        business_implications,
        editorial_analysis,
        article
    )

    response = client.models.generate_content(
        model=get_model(),
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            max_output_tokens=2200
        )
    )

    result = parse_json_response(response.text)

    approved = result.get("approved") is True
    unsupported = result.get("unsupported_claims", [])
    corrected_article = result.get("corrected_article", "").strip()

    if not approved:
        raise ValueError(
            "Article did not pass factual review: "
            + str(unsupported)
        )

    if unsupported:
        raise ValueError(
            "Unsupported claims remain in the article."
        )

    if not corrected_article:
        raise ValueError(
            "Factual review returned an empty article."
        )

    return corrected_article


# --------------------------------------------------
# 5. CONSERVATIVE FACTUAL FALLBACK
# --------------------------------------------------

def generate_fallback_article(
    news,
    extracted_facts,
    business_implications=None,
    editorial_analysis=None
):
    """
    Produce a conservative article using only supplied
    source-backed information.

    This fallback does not invent additional developments.
    """

    facts = clean_list(extracted_facts)
    implications = clean_list(business_implications)
    analysis = clean_list(editorial_analysis)

    if not facts:
        return (
            "Article generation stopped because "
            "no extracted source facts are available."
        )

    title = news.get("title") or "Chemical Industry Update"

    sections = [
        f"# {title}",
        "",
        "## Reported Development",
        "",
        "The selected article reports the following details:",
        ""
    ]

    sections.extend(
        f"- {fact}" for fact in facts
    )

    if implications:
        sections.extend([
            "",
            "## Business Relevance",
            "",
            "The following implications were identified "
            "during source analysis:",
            ""
        ])

        sections.extend(
            f"- {item}" for item in implications
        )

    if analysis:
        sections.extend([
            "",
            "## Industry Perspective",
            "",
            "The following points are editorial analysis "
            "and should not be treated as additional "
            "confirmed facts:",
            ""
        ])

        sections.extend(
            f"- {item}" for item in analysis
        )

    sections.extend([
        "",
        "## Closing Perspective",
        "",
        "Further developments and official announcements "
        "can help industry participants assess the "
        "significance of this news.",
        "",
        "How might this development influence decisions "
        "across the chemical industry?",
        "",
        "#ChemicalIndustry #ChemicalManufacturing "
        "#IndustryInsights #ChemStride"
    ])

    return "\n".join(sections)


# --------------------------------------------------
# 6. MAIN ARTICLE GENERATION FUNCTION
# --------------------------------------------------

def generate_article(
    news,
    verified_facts,
    use_ai=True,
    business_implications=None,
    editorial_analysis=None
):
    """
    Generate a source-grounded ChemStride LinkedIn article.

    Pipeline:
    1. Validate extracted facts.
    2. Generate the article.
    3. Review factual claims.
    4. Return only an approved article.
    5. Use conservative fallback if AI fails.
    """

    facts = clean_list(verified_facts)
    implications = clean_list(business_implications)
    analysis = clean_list(editorial_analysis)

    if not facts:
        return (
            "No extracted facts are available. "
            "Article generation has been stopped."
        )

    if not use_ai:
        return generate_fallback_article(
            news,
            facts,
            implications,
            analysis
        )

    try:
        client = get_gemini_client()

        prompt = create_prompt(
            news,
            facts,
            implications,
            analysis
        )

        print("\nSending article request to Gemini...")

        start_time = time.perf_counter()

        response = client.models.generate_content(
            model=get_model(),
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=2200
            )
        )

        if not response.text or not response.text.strip():
            raise ValueError(
                "Gemini returned an empty article."
            )

        generated_article = response.text.strip()

        print(
            "Article generation time: "
            f"{time.perf_counter() - start_time:.2f} seconds"
        )

        print("Checking article claims against source facts...")

        verified_article = verify_generated_article(
            client,
            news,
            facts,
            implications,
            analysis,
            generated_article
        )

        print("Article passed AI factual review.")

        return verified_article

    except Exception as error:

        print(
            "Article generation or factual review failed:",
            repr(error)
        )

        print(
            "Using conservative source-fact fallback article."
        )

        return generate_fallback_article(
            news,
            facts,
            implications,
            analysis
        )


# --------------------------------------------------
# 7. LOCAL TEST
# --------------------------------------------------

if __name__ == "__main__":

    sample_news = {
        "title": "Example chemical industry development",
        "source": "Example Publisher",
        "published": "Example publication date",
        "link": ""
    }

    sample_facts = [
        "Example company announced a manufacturing development.",
        "The article reports the location of the facility."
    ]

    article = generate_article(
        sample_news,
        sample_facts,
        use_ai=False
    )

    print("\nGENERATED ARTICLE\n")
    print(article)
