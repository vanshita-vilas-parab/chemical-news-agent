
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from modules.style_guide import get_style_guide

load_dotenv()


# --------------------------------------------------
# 1. PREPARE ARTICLE PROMPT
# --------------------------------------------------

def create_prompt(
    news,
    extracted_facts,
    business_implications=None,
    editorial_analysis=None
):
    """Create a factual ChemStride LinkedIn article prompt."""

    style = get_style_guide()

    facts_text = "\n".join(
        f"- {fact}"
        for fact in extracted_facts
    )

    implications_text = "\n".join(
        f"- {item}"
        for item in (business_implications or [])
    ) or "No direct implications were established by the source."

    analysis_text = "\n".join(
        f"- {item}"
        for item in (editorial_analysis or [])
    ) or "No additional editorial analysis is available."

    prompt = f"""
You are writing a professional LinkedIn industry article
for ChemStride.

Follow these writing guidelines:

{style}

SELECTED NEWS:

Headline: {news.get('title', 'Not provided')}
Publisher: {news.get('source', 'Not provided')}
Published: {news.get('published', 'Not provided')}
Original article: {news.get('original_url') or news.get('link') or news.get('url', 'Not provided')}

FACTS EXTRACTED FROM THE ARTICLE:

{facts_text}

BUSINESS IMPLICATIONS SUPPORTED BY THE ARTICLE:

{implications_text}

EDITORIAL ANALYSIS:

{analysis_text}

ARTICLE REQUIREMENTS:

1. Write approximately 300-400 words.
2. Start with a strong, informative headline.
3. Introduce the actual development clearly.
4. Explain the reported facts accurately.
5. Use short paragraphs and meaningful headings.
6. Discuss business implications only when supported.
7. If you add broader interpretation, clearly label it as analysis.
8. Include a practical chemical-industry takeaway.
9. End with a relevant question or call to action.
10. Add 4-6 relevant hashtags.
11. Use simple, natural and professional English.
12. Follow ChemStride's writing style.
13. Avoid unnecessary repetition and generic statements.

STRICT FACTUAL RULES:

- Use only the supplied facts for specific claims.
- Never invent statistics, dates, company statements or quotations.
- Never introduce facts from unrelated developments.
- Do not convert proposals or plans into completed activities.
- Do not present possible market effects as confirmed outcomes.
- Do not invent customer demand, production volumes or financial effects.
- Do not claim that information has been independently verified.
- Do not create unsupported connections to other industries.
- If information is unavailable, leave it out.
- Do not repeat the same fact merely to increase article length.

Return only the complete LinkedIn article.
"""

    return prompt


# --------------------------------------------------
# 2. FACTUAL FALLBACK ARTICLE
# --------------------------------------------------

def generate_fallback_article(
    news,
    extracted_facts,
    business_implications=None,
    editorial_analysis=None
):
    """
    Generate a basic article without adding unsupported facts.
    """

    title = news.get(
        "title",
        "Chemical Industry Update"
    )

    facts_text = "\n".join(
        f"- {fact}"
        for fact in extracted_facts
    )

    implications = business_implications or []
    analysis = editorial_analysis or []

    sections = [
        f"# {title}",
        "",
        "## Understanding the Development",
        "",
        "The selected article reports the following details:",
        "",
        facts_text
    ]

    if implications:

        sections.extend([
            "",
            "## Business Relevance",
            "",
            "The source identifies the following business implications:",
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
            "The following points are editorial analysis, "
            "not additional confirmed facts:",
            ""
        ])

        sections.extend(
            f"- {item}" for item in analysis
        )

    sections.extend([
        "",
        "## Industry Takeaway",
        "",
        "Industry participants can follow this development "
        "and assess its relevance using further company, "
        "market and operational information.",
        "",
        "What could this development mean for businesses "
        "across the chemical industry?",
        "",
        "#ChemicalIndustry #ChemicalManufacturing "
        "#IndustryInsights #ChemStride"
    ])

    return "\n".join(sections)


# --------------------------------------------------
# 3. GENERATE LINKEDIN ARTICLE
# --------------------------------------------------

def generate_article(
    news,
    verified_facts,
    use_ai=True,
    business_implications=None,
    editorial_analysis=None
):
    """
    Generate a ChemStride LinkedIn article.

    AI generation is optional. The fallback uses only
    the extracted facts and supplied analysis.
    """

    if not verified_facts:
        return (
            "No extracted facts are available. "
            "Article generation has been stopped."
        )

    if not use_ai:

        return generate_fallback_article(
            news,
            verified_facts,
            business_implications,
            editorial_analysis
        )

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:

        print(
            "Gemini API key not found. "
            "Using factual fallback article."
        )

        return generate_fallback_article(
            news,
            verified_facts,
            business_implications,
            editorial_analysis
        )

    try:

        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(
                    attempts=1
                )
            )
        )

        prompt = create_prompt(
            news,
            verified_facts,
            business_implications,
            editorial_analysis
        )

        print("\nSending article request to Gemini...")

        start_time = time.perf_counter()

        response = client.models.generate_content(
            model=os.getenv(
                "GEMINI_MODEL",
                "gemini-3.8-flash"
            ),
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=1800
            )
        )

        generation_time = (
            time.perf_counter() - start_time
        )

        print(
            f"Article generation time: "
            f"{generation_time:.2f} seconds"
        )

        if response.text and response.text.strip():
            return response.text.strip()

        print("Gemini returned an empty response.")

    except Exception as error:

        print(
            "Gemini article generation failed:",
            repr(error)
        )

    print("Using factual fallback article.")

    return generate_fallback_article(
        news,
        verified_facts,
        business_implications,
        editorial_analysis
    )


# --------------------------------------------------
# 4. LOCAL TEST
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
