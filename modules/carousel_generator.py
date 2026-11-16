
import os
import json
import re
from io import BytesIO
from xml.sax.saxutils import escape
from urllib.parse import urlparse

from dotenv import load_dotenv
from google import genai
from google.genai import types

from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

load_dotenv()


# ==================================================
# CHEMSTRIDE VISUAL THEME
# ==================================================

NAVY = HexColor("#123447")
NAVY_LIGHT = HexColor("#1D4B60")
TEAL = HexColor("#238C8C")
MINT = HexColor("#DCEFED")
CREAM = HexColor("#F6F5EF")
WHITE = colors.white
DARK_TEXT = HexColor("#203640")
MUTED = HexColor("#61747B")
GOLD = HexColor("#D6A84F")
BORDER = HexColor("#DCE4E2")

# Square LinkedIn carousel
PAGE_W = 720
PAGE_H = 720
MARGIN = 52


# ==================================================
# HELPERS
# ==================================================

def safe_text(value):
    """Prepare text safely for ReportLab."""

    value = str(value or "").strip()

    # Replace unsupported Indian rupee glyph with text.
    value = value.replace("₹", "INR ")

    value = re.sub(r"<[^>]*>", "", value)

    return escape(value).replace("\n", "<br/>")


def get_source_url(news, verified_data):
    sources = verified_data.get("sources", [])

    if sources and isinstance(sources[0], dict):
        url = sources[0].get("url") or sources[0].get("link")

        if url:
            return url

    return (
        news.get("original_url")
        or news.get("link")
        or news.get("url")
        or ""
    )


def get_source_name(news, verified_data):
    sources = verified_data.get("sources", [])

    if sources and isinstance(sources[0], dict):
        name = (
            sources[0].get("name")
            or sources[0].get("publisher")
        )

        if name:
            return name

    return news.get("publisher") or news.get("source") or "Original article"


def short_source_url(url):
    if not url:
        return ""

    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def clean_items(items, limit=4):
    result = []

    for item in items or []:

        if isinstance(item, dict):
            value = (
                item.get("description")
                or item.get("value")
                or item.get("text")
                or ""
            )
        else:
            value = item

        value = str(value).strip()

        if value:
            result.append(value)

        if len(result) >= limit:
            break

    return result


# ==================================================
# AI SLIDE CONTENT
# ==================================================

def create_carousel_prompt(news, verified_data):

    facts = verified_data.get("facts", [])
    figures = verified_data.get("important_figures", [])
    implications = verified_data.get("business_implications", [])

    return f"""
You are creating a professional six-slide LinkedIn carousel
for ChemStride, a chemical industry-focused company.

SELECTED NEWS:
{news.get("title", "")}

MAIN DEVELOPMENT:
{verified_data.get("main_development", "")}

COMPANY:
{verified_data.get("company", "")}

LOCATION:
{verified_data.get("location", "")}

ARTICLE FACTS:
{json.dumps(facts, ensure_ascii=False)}

IMPORTANT FIGURES:
{json.dumps(figures, ensure_ascii=False)}

BUSINESS IMPLICATIONS:
{json.dumps(implications, ensure_ascii=False)}

Create exactly SIX slides.

SLIDE STRUCTURE:

1. COVER
- Strong, concise headline.
- One-line introduction.
- Make the development immediately understandable.

2. THE DEVELOPMENT
- Explain what happened.
- Use actual article details.

3. KEY FACTS
- Highlight important figures and details.
- Do not invent statistics.

4. INDUSTRY PERSPECTIVE
- Explain why the development may matter.
- Separate facts from interpretation.

5. BUSINESS TAKEAWAY
- Give practical points for chemical industry participants.
- Avoid unsupported predictions.

6. CLOSING
- A thoughtful question or concluding message.
- Mention ChemStride.
- Keep room for the original article source reference.

STYLE:
- Professional, clear and approachable.
- Natural business English.
- Short, meaningful sentences.
- Avoid generic motivational statements.
- Avoid repeating the same fact.
- No excessive bullet points.
- No emojis.
- No invented figures or claims.
- Use INR instead of the ₹ symbol.
- Keep headings concise.
- Keep bullets short enough for a square slide.

FACTUAL RULES:
- Use only supplied article information.
- Do not invent dates, numbers, companies or quotations.
- Do not present possible implications as confirmed outcomes.
- If information is unavailable, leave it out.
- Do not claim independent verification.

Return valid JSON only:

{{
  "slides": [
    {{
      "heading": "Slide heading",
      "subheading": "Supporting sentence",
      "bullets": ["Point one", "Point two"],
      "footer": "Short section label"
    }}
  ]
}}

Return exactly six slides.
"""


def validate_slides(slides):

    if not isinstance(slides, list) or len(slides) != 6:
        return False

    for slide in slides:

        if not isinstance(slide, dict):
            return False

        if not isinstance(slide.get("heading"), str):
            return False

        if not isinstance(slide.get("bullets"), list):
            return False

    return True


def generate_slide_content(news, verified_data, use_ai=True):

    if not verified_data or not verified_data.get("facts"):
        raise ValueError("No extracted article facts available.")

    if use_ai and os.getenv("GEMINI_API_KEY"):

        try:

            client = genai.Client(
                api_key=os.getenv("GEMINI_API_KEY"),
                http_options=types.HttpOptions(
                    retry_options=types.HttpRetryOptions(attempts=1)
                )
            )

            response = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
                contents=create_carousel_prompt(news, verified_data),
                config=types.GenerateContentConfig(
                    temperature=0.25,
                    response_mime_type="application/json",
                    max_output_tokens=1800
                )
            )

            if response.text:

                result = json.loads(response.text)
                slides = result.get("slides", [])

                if validate_slides(slides):
                    return slides

            print("AI returned an invalid slide structure.")

        except Exception as error:
            print("Carousel AI generation failed:", repr(error))

    return create_fallback_slides(news, verified_data)


# ==================================================
# FALLBACK SLIDE CONTENT
# ==================================================

def create_fallback_slides(news, verified_data):

    facts = clean_items(verified_data.get("facts", []), 5)
    implications = clean_items(
        verified_data.get("business_implications", []), 3
    )

    title = news.get("title", "Chemical Industry Update")
    main = verified_data.get("main_development", "")
    company = verified_data.get("company", "")
    location = verified_data.get("location", "")

    figure_points = []

    for item in verified_data.get("important_figures", [])[:3]:

        if isinstance(item, dict):

            value = item.get("value", "")
            description = item.get("description", "")

            point = f"{value}: {description}".strip(": ")

            if point:
                figure_points.append(point)

        elif str(item).strip():
            figure_points.append(str(item).strip())

    closing_points = []

    if company:
        closing_points.append(f"Company: {company}")

    if location:
        closing_points.append(f"Location: {location}")

    return [
        {
            "heading": title,
            "subheading": (
                "A closer look at a recent chemical industry development."
            ),
            "bullets": [],
            "footer": "CHEMICAL INDUSTRY INSIGHTS"
        },
        {
            "heading": "What happened?",
            "subheading": main or (
                "The selected article reports the following development."
            ),
            "bullets": facts[:2],
            "footer": "THE DEVELOPMENT"
        },
        {
            "heading": "Key facts",
            "subheading": "Details reported in the source article.",
            "bullets": figure_points or facts[2:5] or facts[:3],
            "footer": "ARTICLE FACTS"
        },
        {
            "heading": "Industry perspective",
            "subheading": "Why this development may matter to the sector.",
            "bullets": implications or [
                "The development is worth monitoring.",
                "Further information is needed to assess its wider impact."
            ],
            "footer": "INDUSTRY PERSPECTIVE"
        },
        {
            "heading": "Business takeaway",
            "subheading": "Points industry participants can consider.",
            "bullets": [
                "Monitor the development and any further announcements.",
                "Assess its relevance to operations, sourcing and business priorities."
            ],
            "footer": "BUSINESS TAKEAWAY"
        },
        {
            "heading": "Stay informed",
            "subheading": (
                "Understanding industry developments helps businesses "
                "make informed decisions."
            ),
            "bullets": closing_points,
            "footer": "CHEMSTRIDE | INDUSTRY INSIGHTS"
        }
    ]


# ==================================================
# PDF DRAWING HELPERS
# ==================================================

def draw_paragraph(pdf, text, x, y_top, width, style):

    if not text:
        return y_top

    paragraph = Paragraph(safe_text(text), style)

    _, height = paragraph.wrap(width, PAGE_H)

    paragraph.drawOn(pdf, x, y_top - height)

    return y_top - height


def draw_bullet_card(pdf, text, x, y_top, width, style):

    paragraph = Paragraph(safe_text(text), style)

    _, text_height = paragraph.wrap(width - 48, 180)

    card_height = max(62, text_height + 30)
    card_y = y_top - card_height

    pdf.setFillColor(WHITE)

    pdf.roundRect(
        x,
        card_y,
        width,
        card_height,
        10,
        fill=1,
        stroke=0
    )

    pdf.setFillColor(TEAL)

    pdf.roundRect(
        x,
        card_y,
        5,
        card_height,
        2,
        fill=1,
        stroke=0
    )

    pdf.setFillColor(TEAL)

    pdf.circle(
        x + 23,
        card_y + card_height / 2,
        3,
        fill=1,
        stroke=0
    )

    paragraph.drawOn(
        pdf,
        x + 38,
        card_y + (card_height - text_height) / 2
    )

    return card_y - 11


def draw_header(pdf, is_cover):

    brand_color = HexColor("#D8E8E9") if is_cover else NAVY
    accent_color = GOLD if is_cover else TEAL

    pdf.setFillColor(accent_color)

    pdf.roundRect(
        MARGIN,
        PAGE_H - 53,
        48,
        4,
        2,
        fill=1,
        stroke=0
    )

    pdf.setFillColor(brand_color)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(MARGIN, PAGE_H - 39, "CHEMSTRIDE")

    pdf.setFont("Helvetica", 9)

    pdf.drawRightString(
        PAGE_W - MARGIN,
        PAGE_H - 39,
        "INDUSTRY INSIGHTS"
    )


def draw_footer(pdf, index, is_cover):

    line_color = HexColor("#416273") if is_cover else BORDER
    text_color = HexColor("#D8E8E9") if is_cover else MUTED

    pdf.setStrokeColor(line_color)
    pdf.setLineWidth(0.8)

    pdf.line(
        MARGIN,
        38,
        PAGE_W - MARGIN,
        38
    )

    pdf.setFillColor(text_color)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(MARGIN, 21, "CHEMSTRIDE")

    pdf.setFont("Helvetica", 9)

    pdf.drawRightString(
        PAGE_W - MARGIN,
        21,
        f"{index + 1:02d} / 06"
    )


# ==================================================
# PDF GENERATION
# ==================================================

def create_pdf(slides, news, verified_data):

    if not validate_slides(slides):
        raise ValueError("Carousel must contain exactly six valid slides.")

    buffer = BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=(PAGE_W, PAGE_H)
    )

    title_style = ParagraphStyle(
        "Title",
        fontName="Helvetica-Bold",
        fontSize=29,
        leading=35,
        textColor=NAVY
    )

    cover_style = ParagraphStyle(
        "Cover",
        fontName="Helvetica-Bold",
        fontSize=36,
        leading=43,
        textColor=WHITE
    )

    sub_style = ParagraphStyle(
        "Subheading",
        fontName="Helvetica",
        fontSize=15,
        leading=21,
        textColor=MUTED
    )

    cover_sub_style = ParagraphStyle(
        "CoverSubheading",
        fontName="Helvetica",
        fontSize=16,
        leading=23,
        textColor=HexColor("#D8E8E9")
    )

    body_style = ParagraphStyle(
        "Body",
        fontName="Helvetica",
        fontSize=13,
        leading=18,
        textColor=DARK_TEXT
    )

    source_url = get_source_url(news, verified_data)
    source_name = get_source_name(news, verified_data)
    source_domain = short_source_url(source_url)

    for index, slide in enumerate(slides):

        is_cover = index == 0
        is_closing = index == 5

        pdf.setFillColor(NAVY if is_cover else CREAM)

        pdf.rect(
            0,
            0,
            PAGE_W,
            PAGE_H,
            fill=1,
            stroke=0
        )

        draw_header(pdf, is_cover)

        footer = slide.get("footer", "")

        pdf.setFillColor(GOLD if is_cover else TEAL)
        pdf.setFont("Helvetica-Bold", 9)

        pdf.drawString(
            MARGIN,
            PAGE_H - 91,
            str(footer).upper()[:65]
        )

        heading_style = cover_style if is_cover else title_style

        y = draw_paragraph(
            pdf,
            slide.get("heading", ""),
            MARGIN,
            PAGE_H - 116,
            PAGE_W - 2 * MARGIN,
            heading_style
        )

        y -= 15

        sub_style_to_use = (
            cover_sub_style if is_cover else sub_style
        )

        y = draw_paragraph(
            pdf,
            slide.get("subheading", ""),
            MARGIN,
            y,
            PAGE_W - 2 * MARGIN,
            sub_style_to_use
        )

        y -= 20

        if is_cover:

            visual_y = 95
            visual_height = 145

            pdf.setFillColor(NAVY_LIGHT)

            pdf.roundRect(
                MARGIN,
                visual_y,
                PAGE_W - 2 * MARGIN,
                visual_height,
                16,
                fill=1,
                stroke=0
            )

            pdf.setFillColor(GOLD)

            pdf.roundRect(
                MARGIN + 24,
                visual_y + 108,
                42,
                4,
                2,
                fill=1,
                stroke=0
            )

            pdf.setFillColor(WHITE)
            pdf.setFont("Helvetica-Bold", 16)

            pdf.drawString(
                MARGIN + 24,
                visual_y + 76,
                "CHEMICAL INDUSTRY"
            )

            pdf.setFillColor(HexColor("#D8E8E9"))
            pdf.setFont("Helvetica", 12)

            pdf.drawString(
                MARGIN + 24,
                visual_y + 49,
                "News | Analysis | Business Perspective"
            )

            pdf.setFillColor(GOLD)

            pdf.circle(
                PAGE_W - MARGIN - 35,
                visual_y + 72,
                14,
                fill=1,
                stroke=0
            )

            pdf.setFillColor(NAVY)
            pdf.setFont("Helvetica-Bold", 12)

            pdf.drawCentredString(
                PAGE_W - MARGIN - 35,
                visual_y + 68,
                "C"
            )

        else:

            bullets = clean_items(slide.get("bullets", []), 4)

            for bullet in bullets:

                if y < 115:
                    break

                y = draw_bullet_card(
                    pdf,
                    bullet,
                    MARGIN,
                    y,
                    PAGE_W - 2 * MARGIN,
                    body_style
                )

            if is_closing:

                source_y = 90

                pdf.setStrokeColor(BORDER)

                pdf.line(
                    MARGIN,
                    source_y + 50,
                    PAGE_W - MARGIN,
                    source_y + 50
                )

                pdf.setFillColor(NAVY)
                pdf.setFont("Helvetica-Bold", 9)

                pdf.drawString(
                    MARGIN,
                    source_y + 32,
                    "ORIGINAL SOURCE"
                )

                pdf.setFillColor(MUTED)
                pdf.setFont("Helvetica", 10)

                pdf.drawString(
                    MARGIN,
                    source_y + 15,
                    str(source_name)[:75]
                )

                if source_domain:

                    pdf.setFillColor(TEAL)
                    pdf.setFont("Helvetica-Bold", 9)

                    pdf.drawString(
                        MARGIN,
                        source_y - 1,
                        source_domain[:75]
                    )

                if source_url.startswith(("http://", "https://")):

                    pdf.linkURL(
                        source_url,
                        (
                            MARGIN,
                            source_y - 8,
                            PAGE_W - MARGIN,
                            source_y + 43
                        ),
                        relative=0
                    )

        draw_footer(pdf, index, is_cover)

        pdf.showPage()

    pdf.save()
    buffer.seek(0)

    return buffer.getvalue()


# ==================================================
# MAIN FUNCTION
# ==================================================

def generate_carousel(news, verified_data, use_ai=True):

    slides = generate_slide_content(
        news,
        verified_data,
        use_ai=use_ai
    )

    pdf_bytes = create_pdf(
        slides,
        news,
        verified_data
    )

    return {
        "slides": slides,
        "pdf": pdf_bytes,
        "filename": "chemstride_linkedin_carousel.pdf"
    }
