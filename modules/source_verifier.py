
import os
import json
import re
import html
import requests

from html.parser import HTMLParser
from urllib.parse import urlparse
from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()


# --------------------------------------------------
# 1. HTML CONTENT EXTRACTOR
# --------------------------------------------------

class ArticleTextParser(HTMLParser):
    """Extract article text, paragraphs and structured content."""

    SKIP_TAGS = {
        "script", "style", "nav", "footer", "header",
        "noscript", "svg", "iframe", "form", "button",
        "aside"
    }

    BLOCK_TAGS = {
        "p", "h1", "h2", "h3", "h4", "li",
        "article", "main", "section", "div"
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)

        self.skip_depth = 0
        self.tag_stack = []
        self.all_text = []
        self.paragraphs = []
        self.article_parts = []
        self.current_paragraph = []
        self.capture_article = False
        self.article_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag in self.SKIP_TAGS:
            self.skip_depth += 1

        if self.skip_depth:
            self.tag_stack.append(tag)
            return

        if tag == "article":
            self.capture_article = True
            self.article_depth += 1

        if tag == "p":
            self.current_paragraph = []

        self.tag_stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self.skip_depth:
            self.skip_depth -= 1

        if not self.tag_stack:
            return

        if tag == "p" and self.current_paragraph:
            paragraph = " ".join(self.current_paragraph).strip()

            if paragraph:
                self.paragraphs.append(paragraph)

                if self.capture_article:
                    self.article_parts.append(paragraph)

            self.current_paragraph = []

        if tag == "article":
            self.article_depth = max(0, self.article_depth - 1)

            if self.article_depth == 0:
                self.capture_article = False

        # Remove the matching tag and any unclosed nested tags.
        if tag in self.tag_stack:
            reverse_index = self.tag_stack[::-1].index(tag)
            index = len(self.tag_stack) - 1 - reverse_index
            self.tag_stack = self.tag_stack[:index]

    def handle_data(self, data):
        if self.skip_depth:
            return

        text = " ".join(data.split())

        if not text:
            return

        self.all_text.append(text)

        if "p" in self.tag_stack:
            self.current_paragraph.append(text)

        if self.capture_article:
            self.article_parts.append(text)


# --------------------------------------------------
# 2. TEXT CLEANING
# --------------------------------------------------

def clean_article_text(text):
    text = html.unescape(str(text or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def unique_paragraphs(paragraphs):
    seen = set()
    output = []

    for paragraph in paragraphs:
        paragraph = clean_article_text(paragraph)

        if len(paragraph) < 35:
            continue

        key = paragraph.lower()

        if key not in seen:
            seen.add(key)
            output.append(paragraph)

    return output


# --------------------------------------------------
# 2A. SOURCE EVIDENCE MATCHING
# --------------------------------------------------

def normalize_evidence_text(text):
    """Normalize text for exact-phrase matching against the fetched article."""
    text = clean_article_text(text).lower()
    text = re.sub(r"[^a-z0-9%₹$.,:/+-]+", " ", text)
    return re.sub(r"\\s+", " ", text).strip()


def match_evidence_quote(article_text, evidence):
    """
    Return True only when a sufficiently substantial evidence quote appears
    in the fetched article text. This is traceability, not independent fact-checking.
    """
    quote = normalize_evidence_text(evidence)
    source = normalize_evidence_text(article_text)
    return len(quote) >= 18 and quote in source


def build_evidence_records(items, evidence_items, article_text, category):
    """Pair extracted claims with evidence quotations and record match status."""
    records = []
    evidence_by_claim = {}

    for evidence_item in evidence_items or []:
        if not isinstance(evidence_item, dict):
            continue
        claim = (
            evidence_item.get("fact")
            or evidence_item.get("implication")
            or evidence_item.get("text")
            or ""
        )
        evidence_by_claim[clean_article_text(claim).casefold()] = (
            evidence_item.get("evidence", "")
        )

    for item in items or []:
        if isinstance(item, dict):
            claim = item.get("text") or item.get("description") or item.get("value") or ""
            evidence = item.get("evidence", "")
        else:
            claim = str(item)
            evidence = ""

        claim = clean_article_text(claim)
        if not claim:
            continue

        if not evidence:
            evidence = evidence_by_claim.get(claim.casefold(), "")

        matched = match_evidence_quote(article_text, evidence)
        records.append({
            "text": claim,
            "evidence": clean_article_text(evidence),
            "evidence_matches_source": matched,
            "evidence_status": (
                "Source quotation matched"
                if matched else "No matching source quotation"
            ),
            "category": category
        })

    return records


def attach_evidence_status(extracted_data, article_text):
    """Attach evidence traceability records without changing legacy fact fields."""
    facts = build_evidence_records(
        extracted_data.get("facts", []),
        extracted_data.get("fact_evidence", []),
        article_text,
        "reported_fact"
    )
    figures = build_evidence_records(
        extracted_data.get("important_figures", []),
        [],
        article_text,
        "reported_figure"
    )
    implications = build_evidence_records(
        extracted_data.get("business_implications", []),
        extracted_data.get("implication_evidence", []),
        article_text,
        "reported_implication"
    )

    all_records = facts + figures + implications
    extracted_data["fact_evidence_records"] = facts
    extracted_data["figure_evidence_records"] = figures
    extracted_data["implication_evidence_records"] = implications
    extracted_data["evidence_summary"] = {
        "total_claims": len(all_records),
        "claims_with_matching_quotes": sum(
            1 for item in all_records if item["evidence_matches_source"]
        ),
        "claims_without_matching_quotes": sum(
            1 for item in all_records if not item["evidence_matches_source"]
        ),
        "note": (
            "Quote matching establishes traceability to the fetched article text; "
            "it does not independently establish that the publisher's claims are true."
        )
    }
    return extracted_data


# --------------------------------------------------
# 3. URL HELPERS
# --------------------------------------------------

def get_article_url(news):
    return (
        news.get("original_url")
        or news.get("link")
        or news.get("url")
        or ""
    )


def get_publisher(news, final_url=None):
    publisher = (
        news.get("publisher")
        or news.get("source")
        or ""
    )

    if publisher:
        return str(publisher)

    if final_url:
        return urlparse(final_url).netloc

    return "Unknown publisher"


def is_valid_http_url(url):
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


# --------------------------------------------------
# 4. JSON-LD ARTICLE EXTRACTION
# --------------------------------------------------

def extract_json_ld(soup_text):
    """Extract articleBody from JSON-LD structured data."""

    article_bodies = []

    scripts = re.findall(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>'
        r'(.*?)</script>',
        soup_text,
        flags=re.IGNORECASE | re.DOTALL
    )

    def inspect_object(obj):
        if isinstance(obj, list):
            for item in obj:
                inspect_object(item)

        elif isinstance(obj, dict):

            article_body = obj.get("articleBody")

            if isinstance(article_body, str):
                cleaned = clean_article_text(article_body)

                if cleaned:
                    article_bodies.append(cleaned)

            for key, value in obj.items():
                if key in ("@graph", "mainEntity", "mainEntityOfPage"):
                    inspect_object(value)

    for script in scripts:

        try:
            data = json.loads(script)
            inspect_object(data)

        except (json.JSONDecodeError, TypeError):
            continue

    if not article_bodies:
        return ""

    return max(article_bodies, key=len)


# --------------------------------------------------
# 5. META DESCRIPTION EXTRACTION
# --------------------------------------------------

def extract_meta_text(page):
    """Read article descriptions and Open Graph metadata."""

    values = []

    patterns = [
        r'<meta[^>]+(?:name|property)=["\']description["\']'
        r'[^>]+content=["\'](.*?)["\']',

        r'<meta[^>]+property=["\']og:description["\']'
        r'[^>]+content=["\'](.*?)["\']',

        r'<meta[^>]+name=["\']twitter:description["\']'
        r'[^>]+content=["\'](.*?)["\']'
    ]

    for pattern in patterns:
        matches = re.findall(
            pattern,
            page,
            flags=re.IGNORECASE | re.DOTALL
        )

        for value in matches:
            cleaned = clean_article_text(value)

            if cleaned:
                values.append(cleaned)

    return " ".join(dict.fromkeys(values))


# --------------------------------------------------
# 6. FETCH ORIGINAL ARTICLE
# --------------------------------------------------

def fetch_article(news):
    """
    Fetch and extract article content.

    Returns:
        article_text
        fetch_message
        final_url
        content_type
    """

    url = get_article_url(news)

    if not url:
        return (
            "",
            "No article URL was provided.",
            "",
            "unavailable"
        )

    if not is_valid_http_url(url):
        return (
            "",
            "The article URL is invalid.",
            url,
            "unavailable"
        )

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive"
    }

    try:
        session = requests.Session()

        response = session.get(
            url,
            headers=headers,
            timeout=(10, 25),
            allow_redirects=True
        )

        status_code = response.status_code
        final_url = response.url

        content_type = response.headers.get(
            "Content-Type", ""
        ).lower()

        if status_code != 200:
            return (
                "",
                f"Publisher returned HTTP {status_code}.",
                final_url,
                "unavailable"
            )

        if "html" not in content_type:
            return (
                "",
                f"Expected HTML but received: {content_type}",
                final_url,
                "unavailable"
            )

        page = response.text

        if not page:
            return (
                "",
                "Publisher returned an empty webpage.",
                final_url,
                "unavailable"
            )

        # Method 1: Structured article data.
        json_ld_text = extract_json_ld(page)

        # Method 2: Article and main HTML sections.
        parser = ArticleTextParser()
        parser.feed(page)

        article_section = clean_article_text(
            " ".join(parser.article_parts)
        )

        # Method 3: Paragraph extraction.
        paragraphs = unique_paragraphs(parser.paragraphs)

        paragraph_text = " ".join(paragraphs)

        # Method 4: Page-wide text.
        full_page_text = clean_article_text(
            " ".join(parser.all_text)
        )

        # Method 5: Article metadata.
        meta_text = extract_meta_text(page)

        # Select the strongest available article-content candidate.
        candidates = [
            ("JSON-LD articleBody", json_ld_text),
            ("Article section", article_section),
            ("Article paragraphs", paragraph_text),
            ("Full page text", full_page_text)
        ]

        method, article_text = max(
            candidates,
            key=lambda item: len(item[1])
        )

        article_text = clean_article_text(article_text)

        # Metadata is diagnostic/supporting context only.
        # It is never used to make an otherwise empty page
        # appear to contain a full article.
        if len(article_text) < 500:

            return (
                "",
                (
                    f"HTTP {status_code}; final URL: {final_url}; "
                    f"extracted characters: {len(article_text)}; "
                    f"method: {method}; "
                    f"metadata characters: {len(meta_text)}. "
                    "The publisher page did not expose enough "
                    "readable article content."
                ),
                final_url,
                "unavailable"
            )

        article_text = article_text[:25000]

        fetch_message = (
            f"HTTP {status_code}; extracted {len(article_text)} "
            f"characters using {method}."
        )

        return (
            article_text,
            fetch_message,
            final_url,
            "full_article"
        )

    except requests.Timeout:
        return (
            "",
            "The publisher webpage request timed out.",
            url,
            "unavailable"
        )

    except requests.RequestException as error:
        return (
            "",
            f"Article fetching failed: {error}",
            url,
            "unavailable"
        )

    except Exception as error:
        return (
            "",
            f"Article extraction failed: {error}",
            url,
            "unavailable"
        )


# --------------------------------------------------
# 7. GEMINI FACT EXTRACTION
# --------------------------------------------------

def extract_facts_with_gemini(news, article_text):

    api_key = os.getenv("GEMINI_API_KEY")

    model = os.getenv(
        "GEMINI_MODEL",
        "gemini-3.8-flash"
    )

    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing.")

    if not article_text or len(article_text) < 500:
        raise ValueError(
            "Insufficient article content for extraction."
        )

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(
            retry_options=types.HttpRetryOptions(
                attempts=3,
                initial_delay=2,
                max_delay=8,
                exp_base=2,
                jitter=0.2
            )
        )
    )

    prompt = f"""
You are a careful chemical-industry news research assistant.

Extract information from the actual article below.

ARTICLE TITLE:
{news.get("title", "Not available")}

ARTICLE PUBLISHER:
{news.get("source", "Not available")}

ARTICLE CONTENT:
{article_text}

STRICT FACTUAL RULES:

1. Use only information explicitly stated in the article.
2. Never invent company names, figures, dates or locations.
3. Do not use outside knowledge to fill missing details.
4. Do not convert a proposal or plan into a completed activity.
5. Keep reported facts separate from interpretation.
6. Do not present assumptions as confirmed developments.
7. If a fact is unavailable, leave it out.
8. Do not claim independent verification.
9. Avoid repeating the same fact.
10. Identify if the article does not match the supplied headline.
11. For each fact, provide a matching exact quotation in "fact_evidence".
12. For each important figure, include an exact supporting "evidence" quotation.
13. For each business implication, provide a matching exact quotation in
    "implication_evidence". Put interpretations in editorial_analysis.
14. Never invent or paraphrase evidence quotations. Leave evidence empty if absent.
15. Include all material names, locations, dates, project stages, figures,
    capacity details and stated objectives present in the article.

Return valid JSON only:

{{
    "title": "Article title",
    "company": "Company name or empty string",
    "location": "Location or empty string",
    "main_development": "What happened according to the article",
    "facts": [
        "A specific fact supported by the article"
    ],
    "fact_evidence": [
        {{
            "fact": "Matching fact above",
            "evidence": "Exact quotation copied from the article"
        }}
    ],
    "important_figures": [
        {{
            "value": "Figure exactly as reported",
            "description": "What the figure represents",
            "evidence": "Exact quotation copied from the article"
        }}
    ],
    "business_implications": [
        "An implication supported by the article"
    ],
    "implication_evidence": [
        {{
            "implication": "Matching implication above",
            "evidence": "Exact quotation copied from the article"
        }}
    ],
    "editorial_analysis": [
        "Clearly labelled interpretation, not a confirmed fact"
    ],
    "missing_information": [
        "Important information not provided by the article"
    ],
    "article_matches_headline": true,
    "extraction_notes": "Any limitations or concerns"
}}

For business_implications, include only implications
supported by the article. Put broader interpretations
in editorial_analysis.
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            max_output_tokens=2500
        )
    )

    if not response.text:
        raise ValueError("Gemini returned an empty response.")

    result = json.loads(response.text)

    if not isinstance(result, dict):
        raise ValueError("Gemini returned invalid JSON.")

    if not isinstance(result.get("facts"), list):
        raise ValueError("Gemini returned an invalid facts structure.")

    result["facts"] = [
        item.strip()
        for item in result["facts"]
        if isinstance(item, str) and item.strip()
    ]

    for field in [
        "important_figures",
        "business_implications",
        "editorial_analysis",
        "missing_information"
    ]:
        if not isinstance(result.get(field), list):
            result[field] = []

    result["important_figures"] = [
        item for item in result["important_figures"]
        if isinstance(item, dict)
    ]

    for evidence_field in ["fact_evidence", "implication_evidence"]:
        if not isinstance(result.get(evidence_field), list):
            result[evidence_field] = []
        result[evidence_field] = [
            item for item in result[evidence_field]
            if isinstance(item, dict)
        ]

    for figure in result["important_figures"]:
        figure.setdefault("evidence", "")

    for field in [
        "business_implications",
        "editorial_analysis",
        "missing_information"
    ]:
        result[field] = [
            item.strip()
            for item in result[field]
            if isinstance(item, str) and item.strip()
        ]

    return result


# --------------------------------------------------
# 8. PROCESS SELECTED NEWS
# --------------------------------------------------

def verify_news(news):

    article_text, fetch_message, final_url, content_type = (
        fetch_article(news)
    )

    if not article_text:

        return {
            "success": False,
            "title": news.get("title", ""),
            "facts": [],
            "sources": [],
            "fetch_message": fetch_message,
            "message": fetch_message,
            "content_type": content_type
        }

    try:

        extracted_data = extract_facts_with_gemini(
            news,
            article_text
        )

        extracted_data = attach_evidence_status(
            extracted_data,
            article_text
        )

        publisher = get_publisher(news, final_url)

        source = {
            "name": publisher,
            "url": final_url
        }

        return {
            "success": True,
            "title": (
                extracted_data.get("title")
                or news.get("title", "")
            ),
            "company": extracted_data.get("company", ""),
            "location": extracted_data.get("location", ""),
            "main_development": extracted_data.get(
                "main_development", ""
            ),
            "facts": extracted_data.get("facts", []),
            "important_figures": extracted_data.get(
                "important_figures", []
            ),
            "business_implications": extracted_data.get(
                "business_implications", []
            ),
            "editorial_analysis": extracted_data.get(
                "editorial_analysis", []
            ),
            "missing_information": extracted_data.get(
                "missing_information", []
            ),
            "extraction_notes": extracted_data.get(
                "extraction_notes", ""
            ),
            "fact_evidence_records": extracted_data.get(
                "fact_evidence_records", []
            ),
            "figure_evidence_records": extracted_data.get(
                "figure_evidence_records", []
            ),
            "implication_evidence_records": extracted_data.get(
                "implication_evidence_records", []
            ),
            "evidence_summary": extracted_data.get(
                "evidence_summary", {}
            ),
            "article_text_length": len(article_text),
            "article_matches_headline": extracted_data.get(
                "article_matches_headline", False
            ),
            "sources": [source],
            "fetch_message": fetch_message,
            "content_type": content_type,
            "verification_status": (
                "Facts extracted from the publisher's article. "
                "Independent verification is still required."
            )
        }

    except Exception as error:

        return {
            "success": False,
            "title": news.get("title", ""),
            "facts": [],
            "sources": [],
            "fetch_message": fetch_message,
            "message": f"Fact extraction failed: {error}",
            "content_type": content_type
        }


# --------------------------------------------------
# 9. ACCESSOR FUNCTIONS
# --------------------------------------------------

def get_verified_facts(result):
    return result.get("facts", [])


def get_sources(result):
    return result.get("sources", [])


def get_evidence_records(result):
    """Return source-quotation traceability records for display or auditing."""
    return {
        "facts": result.get("fact_evidence_records", []),
        "figures": result.get("figure_evidence_records", []),
        "business_implications": result.get("implication_evidence_records", []),
        "summary": result.get("evidence_summary", {})
    }


# --------------------------------------------------
# 10. VALIDATE ARTICLE
# --------------------------------------------------

def validate_news(result):

    if not result.get("success"):
        return (
            False,
            result.get("message", "Article processing failed.")
        )

    if result.get("content_type") != "full_article":
        return (
            False,
            "Full publisher article was not retrieved."
        )

    if not result.get("article_matches_headline"):
        return (
            False,
            "The article could not be confirmed as matching its headline."
        )

    facts = get_verified_facts(result)

    if len(facts) < 2:
        return (
            False,
            "Fewer than two usable facts were extracted."
        )

    if not result.get("main_development"):
        return (
            False,
            "The main development could not be identified."
        )

    sources = get_sources(result)

    if not sources or not sources[0].get("url"):
        return (
            False,
            "No publisher article URL is available."
        )

    return (
        True,
        "Publisher article retrieved; extracted claims include source-quotation "
        "traceability checks. Quote matching is not independent fact verification."
    )


# --------------------------------------------------
# 11. MODULE CHECK
# --------------------------------------------------

if __name__ == "__main__":

    print("CHEMSTRIDE SOURCE VERIFIER")
    print("This module retrieves original publisher article content.")
    print("Use verify_news(news) to extract article facts.")
