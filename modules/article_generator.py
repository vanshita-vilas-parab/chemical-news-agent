
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from modules.style_guide import get_style_guide

load_dotenv()


def create_prompt(news, verified_facts):
    """Prepare instructions and verified information for Gemini."""

    style = get_style_guide()

    facts_text = "\n".join(
        f"- {fact}" for fact in verified_facts
    )

    prompt = f"""
You are writing a LinkedIn industry article for ChemStride.

{style}

NEWS DEVELOPMENT:
Headline: {news.get('title', 'Not provided')}
Publisher: {news.get('source', 'Not provided')}
Published: {news.get('published', 'Not provided')}

VERIFIED FACTS:
{facts_text}

ARTICLE REQUIREMENTS:
- Write approximately 300-450 words.
- Start with an engaging, informative headline.
- Use a natural and professional introduction.
- Explain the development using the verified facts.
- Use clear section headings and short paragraphs.
- Explain its possible business and supply-chain implications.
- Clearly distinguish possible benefits from confirmed outcomes.
- Do not invent statistics, quotations or market predictions.
- Include a meaningful industry takeaway.
- End with a relevant call to action.
- Add 4-6 relevant hashtags.
- Avoid generic introductions and repetitive sentences.
- Return only the complete LinkedIn article.

ADDITIONAL CONTENT RULES:
- Avoid unsupported general claims about rising domestic demand or industry growth.
- Do not describe commissioning as the start of commercial production or operations unless explicitly confirmed by the verified facts.
- Explain that Kutch Chemical will use caustic soda and chlorine for its own production and sales in the Indian market.
- Do not assume that only surplus production will be sold.
- Keep the industry takeaway directly connected to the confirmed plant commissioning, production capacity and technology.
- Do not introduce unsupported statistics, quotations, market trends or company statements.
- Any general industry context must be clearly distinguished from facts about this specific development.
- Do not turn planned activities into completed achievements.
"""

    return prompt


def generate_article(news, verified_facts, use_ai=True):
    """
    Generate a LinkedIn article using Gemini.
    Use a factual fallback draft if the API is unavailable.
    """

    if not verified_facts:
        return "Please provide verified facts before generating the article."

    # Try Gemini when AI generation is enabled
    api_key = os.getenv("GEMINI_API_KEY")

    if use_ai and api_key:

        try:
            client = genai.Client(
                api_key=api_key,
                http_options=types.HttpOptions(
                    retry_options=types.HttpRetryOptions(
                        attempts=1
                    )
                )
            )

            prompt = create_prompt(news, verified_facts)

            print("\nSending article request to Gemini...")
            start_time = time.perf_counter()

            response = client.models.generate_content(
                model=os.getenv(
                    "GEMINI_MODEL",
                    "gemini-3.8-flash"
                ),
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    max_output_tokens=2000,
                )
            )

            generation_time = time.perf_counter() - start_time

            print(
                f"Gemini generation time: "
                f"{generation_time:.2f} seconds"
            )

            finish_reason = None

            if response.candidates:
                finish_reason = response.candidates[0].finish_reason
                print("Gemini finish reason:", finish_reason)

            if response.text:
                if "MAX_TOKENS" in str(finish_reason):
                    print("Warning: Article may be incomplete.")

                return response.text.strip()

            print("Gemini returned an empty response.")

        except Exception as error:
            print("Gemini generation failed:", repr(error))
            print("Using basic fallback draft.")

    elif use_ai and not api_key:
        print("Gemini API key not found. Using fallback draft.")

    # Fallback article: uses only the supplied information
    facts = "\n".join(
        f"- {fact}" for fact in verified_facts
    )

    return f"""
# {news.get('title', 'Chemical Industry Update')}

A new development in India's chemical manufacturing
sector highlights the importance of domestic production
capacity and modern manufacturing technology.

## A New Manufacturing Facility in Gujarat

{facts}

## Industry Significance

The commissioning of this facility adds to India's
caustic soda production capacity.

The use of modern electrolyzer technology is an
important part of this manufacturing development.
Kutch Chemical's planned use of caustic soda and
chlorine for its own production and sales in India
also highlights the role of integrated manufacturing.

For industry participants, developments like this
are worth monitoring when assessing domestic
production capacity and sourcing opportunities.

## Industry Takeaway

The commissioning of the plant represents a
significant addition to India's chemical manufacturing
infrastructure. Its longer-term impact on supply,
pricing and market availability will depend on
operational performance and market conditions.

#ChemicalIndustry #ChemicalManufacturing
#ChlorAlkali #SupplyChain #ChemStride
"""


if __name__ == "__main__":

    sample_news = {
        "title": "Kutch Chemical commissions a major caustic soda plant",
        "source": "thyssenkrupp nucera",
        "published": "5 November 2026"
    }

    sample_facts = [
        "The plant has an annual caustic soda capacity of 220,000 metric tonnes.",
        "The facility is located in Padana, Gujarat.",
        "The plant was commissioned on 5 November 2026.",
        "The facility uses five electrolyzers based on BM Generation 6+ technology.",
        "Kutch Chemical plans to use caustic soda and chlorine for its own production and sales in India."
    ]

    article = generate_article(
        sample_news,
        sample_facts,
        use_ai=False
    )

    print("\nGENERATED ARTICLE\n")
    print(article)
