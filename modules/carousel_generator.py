import os
import json
import re
import html
import requests
from io import BytesIO
from pathlib import Path
from urllib.parse import quote
from xml.sax.saxutils import escape

from dotenv import load_dotenv
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None
    ImageOps = None

load_dotenv()

PAGE_W = 720
PAGE_H = 720
MARGIN = 48
BASE_DIR = Path(__file__).resolve().parent.parent
LOGO_PATH = BASE_DIR / "assets" / "chemstride_logo.png"

THEMES = {
    "Corporate Dark": {"background": "#172326", "panel": "#223438", "text": "#F5F7F5", "muted": "#C2CECB", "accent": "#E21B23", "card": "#26383B"},
    "Clean Editorial": {"background": "#FAFAF6", "panel": "#EDEFEA", "text": "#172326", "muted": "#596568", "accent": "#D9272E", "card": "#FFFFFF"},
    "Sustainability": {"background": "#EDF4EF", "panel": "#D8E8DE", "text": "#173D32", "muted": "#526D61", "accent": "#24845D", "card": "#FFFFFF"},
    "Executive Premium": {"background": "#171717", "panel": "#29251F", "text": "#F7F1E5", "muted": "#C9BFA9", "accent": "#D6A84F", "card": "#292929"},
    "Data & Technology": {"background": "#10243D", "panel": "#193A5B", "text": "#F3F8FF", "muted": "#B8CDE0", "accent": "#38B6D9", "card": "#1A3551"},
    "Industrial Editorial": {"background": "#242424", "panel": "#343434", "text": "#FFFFFF", "muted": "#C9C9C9", "accent": "#E4473F", "card": "#303030"},
}

STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "will",
    "has", "have", "its", "are", "was", "were", "about", "what", "why",
    "how", "could", "would", "should", "their", "company", "industry",
    "chemical", "chemicals", "update", "business", "reported", "according",
    "article", "development", "key", "facts", "looking", "ahead"
}

def safe_text(value):
    value = html.unescape(str(value or "")).replace("₹", "INR ")
    value = re.sub(r"<[^>]*>", "", value)
    return escape(value).replace("\n", "<br/>")

def clean_items(items, limit=None):
    output, seen = [], set()
    for item in items or []:
        if isinstance(item, dict):
            item = item.get("text") or item.get("description") or item.get("value") or ""
        item = re.sub(r"\s+", " ", str(item or "")).strip()
        key = item.casefold()
        if item and key not in seen:
            seen.add(key)
            output.append(item)
        if limit and len(output) >= limit:
            break
    return output

def get_source_url(news, verified_data):
    sources = verified_data.get("sources") or []
    if sources and isinstance(sources[0], dict):
        url = sources[0].get("url") or sources[0].get("link")
        if url:
            return url
    return news.get("original_url") or news.get("link") or news.get("url") or ""

def get_source_name(news, verified_data):
    sources = verified_data.get("sources") or []
    if sources and isinstance(sources[0], dict):
        name = sources[0].get("name") or sources[0].get("publisher")
        if name:
            return name
    return news.get("publisher") or news.get("source") or "Original article"

def choose_theme(news, theme_choice="Auto"):
    if theme_choice in THEMES:
        return theme_choice
    text = f'{news.get("title", "")} {news.get("description", "")}'.lower()
    if any(w in text for w in ("green", "sustainability", "renewable", "carbon", "recycling", "environment")):
        return "Sustainability"
    if any(w in text for w in ("ai", "technology", "digital", "automation", "research")):
        return "Data & Technology"
    if any(w in text for w in ("investment", "acquisition", "merger", "crore", "billion", "funding")):
        return "Executive Premium"
    if any(w in text for w in ("manufacturing", "plant", "factory", "production", "capacity", "expansion")):
        return "Industrial Editorial"
    return "Corporate Dark"

def _tokens(text):
    return {w for w in re.findall(r"[a-zA-Z0-9]{3,}", str(text).lower()) if w not in STOPWORDS}

def _slide_search_text(news, slide, index):
    # Search using story-specific entities plus each slide's own content.
    story = str(news.get("title", ""))
    slide_text = " ".join([
        str(slide.get("heading", "")),
        str(slide.get("subheading", "")),
        " ".join(clean_items(slide.get("bullets", []), 4))
    ])
    return f"{story} {slide_text}"

def search_relevant_commons_image(query, used_titles=None):
    """
    Search Wikimedia Commons for a topic-specific image.
    A result is used only if its title/description has a meaningful lexical
    overlap with the requested subject. Otherwise the slide uses a graphic.
    """
    used_titles = used_titles if used_titles is not None else set()
    terms = list(_tokens(query))
    if not terms:
        return None
    search_query = " ".join(terms[:7])
    api = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"filetype:bitmap {search_query}",
        "gsrnamespace": 6, "gsrlimit": 12,
        "prop": "imageinfo", "iiprop": "url|extmetadata",
        "iiurlwidth": 1000
    }
    try:
        response = requests.get(api, params=params, timeout=8,
                                headers={"User-Agent": "ChemStrideNewsAgent/1.0 (article research)"})
        response.raise_for_status()
        pages = response.json().get("query", {}).get("pages", {})
        candidates = []
        for page in pages.values():
            title = page.get("title", "")
            if title in used_titles:
                continue
            info = (page.get("imageinfo") or [{}])[0]
            image_url = info.get("thumburl") or info.get("url")
            if not image_url:
                continue
            metadata = info.get("extmetadata") or {}
            description = metadata.get("ImageDescription", {}).get("value", "")
            searchable = re.sub(r"<[^>]+>", " ", f"{title} {description}")
            candidate_tokens = _tokens(searchable)
            overlap = len(set(terms) & candidate_tokens)
            score = overlap / max(1, min(len(set(terms)), 5))
            # Require at least two matching subject terms, or a strong single match.
            if overlap >= 2 and score >= 0.25:
                candidates.append((score, title, image_url))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        score, title, image_url = candidates[0]
        used_titles.add(title)
        selected_page = next((p for p in pages.values() if p.get("title") == title), {})
        info = (selected_page.get("imageinfo") or [{}])[0]
        metadata = info.get("extmetadata") or {}
        creator = re.sub(r"<[^>]+>", " ", metadata.get("Artist", {}).get("value", ""))
        license_name = metadata.get("LicenseShortName", {}).get("value", "")
        return {
            "title": title, "url": image_url, "score": score,
            "creator": re.sub(r"\\s+", " ", creator).strip()[:70],
            "license": str(license_name)[:35]
        }
    except Exception as exc:
        print(f"Wikimedia image search skipped: {exc}")
        return None

def verify_image_relevance(image_url, news, slide):
    """Use Gemini Vision to check the actual image against this slide.

    Fail closed: if the image cannot be checked, it is not used. The PDF
    renderer will show the existing branded topic graphic instead.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Image rejected: GEMINI_API_KEY is unavailable.")
        return False

    try:
        response = requests.get(
            image_url,
            timeout=12,
            headers={"User-Agent": "ChemStrideNewsAgent/1.0"},
        )
        response.raise_for_status()
        image_bytes = response.content
        mime_type = response.headers.get("Content-Type", "image/jpeg").split(";")[0]
        if not mime_type.startswith("image/"):
            print("Image rejected: response was not an image.")
            return False

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        prompt = f"""
        Decide whether the attached image is visually relevant to this exact
        ChemStride news slide. Judge the visible contents of the image, not
        merely its filename, URL, or search metadata.

        ARTICLE TITLE: {news.get('title', '')}
        COMPANY: {news.get('company', '') or ''}
        LOCATION: {news.get('location', '') or ''}
        SLIDE HEADING: {slide.get('heading', '')}
        SLIDE SUBHEADING: {slide.get('subheading', '')}
        SLIDE POINTS: {json.dumps(slide.get('bullets', []), ensure_ascii=False)}

        Rules:
        - Accept a generic industrial image only when it clearly illustrates
          the slide's subject at an industry level.
        - Do not claim a generic factory is the named company's actual site.
        - Reject unrelated diagrams, screenshots, maps, cartoons, logos,
          decorative images, and images whose subject cannot be identified.
        - A company-specific claim requires a clearly identifiable company
          facility, product, or equipment; do not infer identity from context.

        Return JSON only:
        {{"relevant": true, "confidence": 0.0, "reason": "brief reason"}}
        """

        result = client.models.generate_content(
            model=os.getenv("GEMINI_VISION_MODEL", os.getenv("GEMINI_MODEL", "gemini-3.8-flash")),
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                max_output_tokens=180,
            ),
        )
        verdict = json.loads(result.text or "{}")
        confidence = float(verdict.get("confidence", 0))
        accepted = verdict.get("relevant") is True and confidence >= 0.75
        print(
            f"Image relevance check: {'ACCEPT' if accepted else 'REJECT'} "
            f"({confidence:.2f}) - {verdict.get('reason', 'No reason supplied')}"
        )
        return accepted

    except Exception as exc:
        print(f"Image verification failed; using branded graphic: {exc}")
        return False


def download_image(image_url):
    try:
        response = requests.get(image_url, timeout=10,
                                headers={"User-Agent": "ChemStrideNewsAgent/1.0"})
        response.raise_for_status()
        if Image and ImageOps:
            im = Image.open(BytesIO(response.content)).convert("RGB")
            im = ImageOps.fit(im, (900, 1200), method=Image.Resampling.LANCZOS)
            out = BytesIO()
            im.save(out, "JPEG", quality=88)
            out.seek(0)
            return ImageReader(out)
        return ImageReader(BytesIO(response.content))
    except Exception as exc:
        print(f"Image download failed: {exc}")
        return None

def load_logo():
    if LOGO_PATH.exists():
        try:
            return ImageReader(str(LOGO_PATH))
        except Exception as exc:
            print(f"Logo loading failed: {exc}")
    return None

def _fact_groups(verified_data):
    facts = clean_items(verified_data.get("facts", []))
    figures = []
    story_text = str(news_title := verified_data.get("title", "")).lower()
    pharma_story = any(term in story_text for term in (
        "pharma", "pharmaceutical", "drug", "medicine", "raw material"
    ))
    for item in verified_data.get("important_figures", []) or []:
        if isinstance(item, dict):
            value = str(item.get("value", "")).strip()
            desc = str(item.get("description", "")).strip()
            text = f"{value}: {desc}".strip(": ")
        else:
            text = str(item).strip()
        # Exclude unrelated historical/surgical facts from a pharmaceutical
        # industry carousel even if they appeared elsewhere in the article.
        if pharma_story and any(term in text.lower() for term in (
            "amputation", "ancient surgery", "surgical procedure", "years old skeleton"
        )):
            continue
        if text:
            figures.append(text)
    implications = clean_items(verified_data.get("business_implications", []))
    analysis = clean_items(verified_data.get("editorial_analysis", []))
    return facts, clean_items(figures), implications, analysis

def create_fallback_slides(news, verified_data):
    facts, figures, implications, analysis = _fact_groups(verified_data)
    title = str(news.get("title") or verified_data.get("title") or "Chemical Industry Update")
    main = str(verified_data.get("main_development") or "").strip()
    if not facts and not figures and not main:
        raise ValueError("No usable article facts are available; carousel generation stopped.")

    # Keep factual content verbatim from the source-verification output.
    # Split facts across slides instead of dropping the majority of them.
    fact_pool = facts[:]
    figure_pool = figures[:]
    implication_pool = implications[:]
    analysis_pool = analysis[:]

    slides = [
        {"heading": title, "subheading": main or "The reported development and its relevance to the chemical industry.", "bullets": [], "footer": "CHEMSTRIDE INDUSTRY UPDATE"},
        {"heading": "What happened?", "subheading": main or "The development reported by the publisher.", "bullets": fact_pool[:3], "footer": "THE DEVELOPMENT"},
        {"heading": "Key facts and figures", "subheading": "Details and numbers explicitly reported in the article.", "bullets": (figure_pool + fact_pool[3:])[:4], "footer": "ARTICLE FACTS"},
        {"heading": "Industry perspective", "subheading": "Source-supported business implications and clearly labelled analysis.", "bullets": (["Reported implication: " + x for x in implication_pool[:2]] + ["Analysis: " + x for x in analysis_pool[:2]])[:4], "footer": "INDUSTRY PERSPECTIVE"},
        {"heading": "Business considerations", "subheading": "Practical considerations arising from the reported development.", "bullets": (implication_pool[2:] + analysis_pool[2:] + fact_pool[6:])[:4], "footer": "BUSINESS TAKEAWAY"},
        {"heading": "Looking ahead", "subheading": "What to monitor as this story develops.", "bullets": (["Information not stated in the article: " + x for x in clean_items(verified_data.get("missing_information", []), 2)] + fact_pool[-2:])[:3], "footer": "CHEMSTRIDE INSIGHTS"},
    ]

    # Do not insert generic filler when a slide has no supported material.
    for slide in slides:
        slide["bullets"] = clean_items(slide.get("bullets", []), 4)
    return slides

def create_carousel_prompt(news, verified_data):
    facts, figures, implications, analysis = _fact_groups(verified_data)
    return f"""
Create a six-slide LinkedIn carousel for ChemStride using ONLY the source material below.
Do not add facts from your own knowledge.

STORY: {news.get("title", "")}
MAIN DEVELOPMENT: {verified_data.get("main_development", "")}
FACTS (must be represented across the slides): {json.dumps(facts, ensure_ascii=False)}
FIGURES: {json.dumps(figures, ensure_ascii=False)}
SOURCE-SUPPORTED BUSINESS IMPLICATIONS: {json.dumps(implications, ensure_ascii=False)}
EDITORIAL ANALYSIS (label as analysis, never as fact): {json.dumps(analysis, ensure_ascii=False)}
MISSING INFORMATION: {json.dumps(verified_data.get("missing_information", []), ensure_ascii=False)}

Create exactly six slides:
1. Cover: accurate headline and concise summary.
2. What happened: explain the event and actors.
3. Key facts and figures: include the most important reported facts and every material figure.
4. Industry perspective: separate reported implications from editorial analysis.
5. Business considerations: specific, practical implications only; no invented recommendations.
6. Looking ahead: identify what remains unknown or what future announcement can be monitored. Do not predict outcomes.

Rules:
- Use all material facts and figures across the six slides; do not omit important facts merely to make slides shorter.
- Do not invent details, dates, statistics, companies, locations, causes or outcomes.
- Never describe a plan as completed.
- Preserve the distinction between INR amounts, capacity, revenue, investment and other measures.
- No generic filler. If the source has no information for a section, say so briefly.
- Each slide may contain up to 4 concise bullets.
- Return valid JSON only: {{"slides":[{{"heading":"...","subheading":"...","bullets":["..."],"footer":"..."}}]}}
"""

def validate_slides(slides):
    if not isinstance(slides, list) or len(slides) != 6:
        return False
    for slide in slides:
        if not isinstance(slide, dict):
            return False
        if not isinstance(slide.get("heading"), str) or not slide["heading"].strip():
            return False
        if not isinstance(slide.get("subheading", ""), str):
            return False
        if not isinstance(slide.get("bullets"), list):
            return False
        if any(not isinstance(x, str) or not x.strip() for x in slide["bullets"]):
            return False
        if len(slide["bullets"]) > 4:
            return False
    return True

def generate_slide_content(news, verified_data, use_ai=True):
    facts, figures, implications, analysis = _fact_groups(verified_data)
    if not facts and not figures and not verified_data.get("main_development"):
        raise ValueError("No extracted article facts are available.")
    if use_ai and os.getenv("GEMINI_API_KEY"):
        try:
            from google import genai
            from google.genai import types
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
                    temperature=0.1,
                    response_mime_type="application/json",
                    max_output_tokens=2600
                )
            )
            if response.text:
                slides = json.loads(response.text).get("slides", [])
                if validate_slides(slides):
                    # AI copy must retain a traceable connection to source content.
                    # If it fails validation, use the deterministic fact-led layout.
                    all_source = " ".join(facts + figures + implications + analysis).lower()
                    generated = " ".join(
                        [s.get("subheading", "") for s in slides] +
                        [b for s in slides for b in s.get("bullets", [])]
                    ).lower()
                    source_terms = _tokens(all_source)
                    generated_terms = _tokens(generated)
                    if not source_terms or len(source_terms & generated_terms) / len(source_terms) >= 0.20:
                        return slides
        except Exception as exc:
            print(f"Carousel AI generation failed; using source-led layout: {exc}")
    return create_fallback_slides(news, verified_data)

def draw_background(pdf, theme):
    pdf.setFillColor(HexColor(theme["background"]))
    pdf.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    pdf.setFillColor(HexColor(theme["panel"]))
    pdf.circle(PAGE_W + 5, PAGE_H + 5, 125, fill=1, stroke=0)

def draw_logo(pdf, logo, theme):
    if logo:
        try:
            pdf.drawImage(logo, PAGE_W - MARGIN - 135, PAGE_H - 77,
                          width=135, height=43, preserveAspectRatio=True, mask="auto")
            return
        except Exception as exc:
            print(f"Logo rendering failed: {exc}")
    pdf.setFillColor(HexColor(theme["text"]))
    pdf.setFont("Helvetica-Bold", 17)
    pdf.drawRightString(PAGE_W - MARGIN, PAGE_H - 58, "ChemStride")

def draw_footer(pdf, index, theme):
    pdf.setStrokeColor(HexColor(theme["muted"]))
    pdf.setLineWidth(0.6)
    pdf.line(MARGIN, 43, PAGE_W - MARGIN, 43)
    pdf.setFillColor(HexColor(theme["muted"]))
    pdf.setFont("Helvetica-Bold", 8)
    pdf.drawString(MARGIN, 25, "CHEMSTRIDE | GLOBAL SOURCING & MARKETING CHEMICALS")
    pdf.setFillColor(HexColor(theme["accent"]))
    pdf.drawRightString(PAGE_W - MARGIN, 25, f"{index + 1:02d} / 06")

def draw_wrapped_text(pdf, text, x, y, width, style, max_height=170):
    if not text:
        return y
    para = Paragraph(safe_text(text), style)
    _, height = para.wrap(width, max_height)
    height = min(height, max_height)
    para.drawOn(pdf, x, y - height)
    return y - height

def draw_bullet(pdf, text, x, y, width, theme, number):
    style = ParagraphStyle(
        f"bullet_{number}", fontName="Helvetica-Bold",
        fontSize=10.5, leading=14,
        textColor=HexColor(theme["text"])
    )
    para = Paragraph(safe_text(text), style)
    _, height = para.wrap(width - 54, 150)
    card_h = max(53, height + 20)
    card_y = y - card_h
    pdf.setFillColor(HexColor(theme["card"]))
    pdf.roundRect(x, card_y, width, card_h, 10, fill=1, stroke=0)
    pdf.setFillColor(HexColor(theme["accent"]))
    pdf.circle(x + 25, card_y + card_h / 2, 13, fill=1, stroke=0)
    pdf.setFillColor(HexColor(theme["background"]))
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawCentredString(x + 25, card_y + card_h / 2 - 3, str(number))
    para.drawOn(pdf, x + 47, card_y + (card_h - height) / 2)
    return card_y - 9

def draw_topic_graphic(pdf, category, box, theme, slide_index, news=None, slide=None):
    """Draw a clean, topic-aware ChemStride illustration using vector shapes only.

    The graphic is illustrative, not a photograph of a named facility. It never
    inserts figures, company names, investment values, or claims from another story.
    """
    x, y, w, h = box
    cx, cy = x + w / 2, y + h / 2 + 12
    accent = HexColor(theme["accent"])
    text = HexColor(theme["text"])
    muted = HexColor(theme["muted"])
    panel = HexColor(theme["panel"])
    bg = HexColor(theme["background"])

    pdf.setFillColor(panel)
    pdf.roundRect(x, y, w, h, 14, fill=1, stroke=0)
    pdf.setStrokeColor(accent)
    pdf.setLineWidth(4)
    pdf.line(x + 18, y + 25, x + 18, y + h - 25)

    story_text = " ".join([
        str((news or {}).get("title", "")),
        str((slide or {}).get("heading", "")),
        str((slide or {}).get("subheading", "")),
        " ".join(clean_items((slide or {}).get("bullets", []), 4)),
    ]).lower()
    pharma = any(term in story_text for term in (
        "pharma", "pharmaceutical", "drug", "medicine", "raw material",
        "active ingredient", "api", "healthcare", "natural-based"
    ))
    sustainability = any(term in story_text for term in (
        "sustainability", "green", "renewable", "carbon", "recycling"
    ))
    supply = any(term in story_text for term in (
        "supply", "import", "export", "self-reliance", "dependence", "sourcing"
    ))

    def molecule(center_x, center_y, scale=1.0):
        pts = [(-42, 8), (-18, 38), (18, 34), (43, 2), (18, -32), (-22, -30)]
        pts = [(center_x + a * scale, center_y + b * scale) for a, b in pts]
        pdf.setStrokeColor(muted)
        pdf.setLineWidth(3)
        for i in range(len(pts)):
            p1, p2 = pts[i], pts[(i + 1) % len(pts)]
            pdf.line(p1[0], p1[1], p2[0], p2[1])
        for i, (px, py) in enumerate(pts):
            pdf.setFillColor(accent if i % 2 == 0 else text)
            pdf.circle(px, py, 9 * scale, fill=1, stroke=0)
        pdf.setFillColor(bg)
        pdf.circle(center_x, center_y, 12 * scale, fill=1, stroke=0)

    def capsule(center_x, center_y, angle=35):
        pdf.saveState()
        pdf.translate(center_x, center_y)
        pdf.rotate(angle)
        pdf.setFillColor(text)
        pdf.roundRect(-42, -15, 84, 30, 15, fill=1, stroke=0)
        pdf.setFillColor(accent)
        pdf.roundRect(0, -15, 42, 30, 15, fill=1, stroke=0)
        pdf.setStrokeColor(panel)
        pdf.setLineWidth(1.5)
        pdf.line(0, -14, 0, 14)
        pdf.restoreState()

    def flask(center_x, center_y):
        p = pdf.beginPath()
        p.moveTo(center_x - 12, center_y + 45)
        p.lineTo(center_x + 12, center_y + 45)
        p.lineTo(center_x + 12, center_y + 8)
        p.lineTo(center_x + 43, center_y - 42)
        p.curveTo(center_x + 48, center_y - 54, center_x + 36, center_y - 62, center_x + 25, center_y - 62)
        p.lineTo(center_x - 25, center_y - 62)
        p.curveTo(center_x - 36, center_y - 62, center_x - 48, center_y - 54, center_x - 43, center_y - 42)
        p.lineTo(center_x - 12, center_y + 8)
        p.close()
        pdf.setFillColor(bg)
        pdf.setStrokeColor(text)
        pdf.setLineWidth(4)
        pdf.drawPath(p, fill=1, stroke=1)
        pdf.setFillColor(accent)
        pdf.wedge(center_x - 34, center_y - 54, center_x + 34, center_y - 8, 180, 180, fill=1, stroke=0)

    def network(center_x, center_y):
        pts = [(-58, 15), (-22, 48), (24, 43), (58, 2), (20, -43), (-34, -38)]
        pts = [(center_x + a, center_y + b) for a, b in pts]
        pdf.setStrokeColor(muted)
        pdf.setLineWidth(3)
        links = [(0,1),(1,2),(2,3),(3,4),(4,5),(5,0),(0,3),(1,4)]
        for a,b in links:
            pdf.line(pts[a][0], pts[a][1], pts[b][0], pts[b][1])
        for i,(px,py) in enumerate(pts):
            pdf.setFillColor(accent if i % 2 == 0 else text)
            pdf.circle(px, py, 11, fill=1, stroke=0)

    def globe(center_x, center_y):
        pdf.setStrokeColor(text)
        pdf.setLineWidth(3)
        pdf.circle(center_x, center_y, 66, fill=0, stroke=1)
        pdf.ellipse(center_x - 30, center_y - 66, center_x + 30, center_y + 66, fill=0, stroke=1)
        pdf.ellipse(center_x - 60, center_y - 28, center_x + 60, center_y + 28, fill=0, stroke=1)
        pdf.setStrokeColor(accent)
        pdf.setLineWidth(2)
        pdf.line(center_x - 55, center_y, center_x + 55, center_y)

    # Six slide positions use different motifs, but all are tied to the story topic.
    if pharma and slide_index in (0, 1):
        molecule(cx, cy + 10, 1.15)
        capsule(cx + 8, cy - 82, 0)
        label = "PHARMACEUTICAL RAW MATERIALS"
    elif pharma and slide_index == 2:
        capsule(cx - 32, cy + 18, -28)
        capsule(cx + 38, cy - 35, 28)
        molecule(cx, cy + 92, 0.62)
        label = "INDUSTRY FACTS & FIGURES"
    elif pharma and slide_index == 3:
        flask(cx, cy + 5)
        molecule(cx + 66, cy - 75, 0.42)
        label = "RESEARCH & DEVELOPMENT"
    elif supply or slide_index == 4:
        network(cx, cy + 8)
        label = "RAW MATERIAL SUPPLY NETWORK"
    elif sustainability:
        # Leaf-like motif: two clean bezier leaves around a central stem.
        pdf.setStrokeColor(text)
        pdf.setLineWidth(4)
        pdf.line(cx - 5, cy - 65, cx + 10, cy + 65)
        pdf.setFillColor(accent)
        pdf.ellipse(cx - 65, cy - 8, cx + 4, cy + 48, fill=1, stroke=0)
        pdf.ellipse(cx + 2, cy - 42, cx + 70, cy + 14, fill=1, stroke=0)
        label = "SUSTAINABLE INDUSTRY"
    elif slide_index == 5:
        globe(cx, cy + 8)
        molecule(cx + 60, cy - 70, 0.38)
        label = "GLOBAL INDUSTRY OUTLOOK"
    else:
        molecule(cx, cy + 10, 1.0)
        label = "CHEMICAL INDUSTRY"

    pdf.setFillColor(text)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawCentredString(cx, y + 45, label[:36])
    pdf.setFillColor(muted)
    pdf.setFont("Helvetica", 7)
    pdf.drawCentredString(cx, y + 29, "ILLUSTRATIVE GRAPHIC")

def infer_image_query(news, slide, index):
    # Prioritise proper nouns and the slide's actual subject, not broad random categories.
    story_title = str(news.get("title", ""))
    slide_content = " ".join([
        str(slide.get("heading", "")),
        str(slide.get("subheading", "")),
        " ".join(clean_items(slide.get("bullets", []), 3))
    ])
    text = f"{story_title} {slide_content}"
    category = "industry"
    rules = [
        ("sustainability", ("renewable", "solar", "carbon", "emission", "recycling", "sustainability")),
        ("laboratory", ("laboratory", "research", "testing", "formulation", "r&d")),
        ("logistics", ("export", "import", "shipping", "warehouse", "logistics", "supply chain")),
        ("technology", ("automation", "digital", "technology", "engineering", "robotics")),
        ("factory", ("manufacturing", "factory", "plant", "production", "facility", "capacity")),
    ]
    lower = text.lower()
    for cat, words in rules:
        if any(w in lower for w in words):
            category = cat
            break
    terms = list(_tokens(text))
    # Keep the company/location/topic in the query by using original text.
    query = " ".join(terms[:8])
    return query, category

def create_pdf(slides, news, verified_data, theme_name):
    if not validate_slides(slides):
        raise ValueError("Carousel must contain exactly six valid slides.")
    theme = THEMES[theme_name]
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=(PAGE_W, PAGE_H))
    logo = load_logo()
    source_url = get_source_url(news, verified_data)
    source_name = get_source_name(news, verified_data)
    used_images = set()

    heading_style = ParagraphStyle("Heading", fontName="Helvetica-Bold", fontSize=25, leading=29, textColor=HexColor(theme["text"]))
    cover_style = ParagraphStyle("Cover", fontName="Helvetica-Bold", fontSize=27, leading=31, textColor=HexColor(theme["text"]))
    sub_style = ParagraphStyle("Sub", fontName="Helvetica", fontSize=11, leading=15, textColor=HexColor(theme["muted"]))

    for index, slide in enumerate(slides):
        draw_background(pdf, theme)
        draw_logo(pdf, logo, theme)
        pdf.setFillColor(HexColor(theme["accent"]))
        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(MARGIN, PAGE_H - 100, str(slide.get("footer", "")).upper()[:55])

        image_box = (438, 190, 230, 350)
        query, category = infer_image_query(news, slide, index)
        # Submission-safe mode: use story-aware branded vector graphics only.
        # This prevents unrelated Wikimedia search results from entering the PDF.
        image_result = None
        draw_topic_graphic(pdf, category, image_box, theme, index, news, slide)
        category_label = "CHEMSTRIDE | ILLUSTRATIVE GRAPHIC"

        pdf.setFillColor(HexColor(theme["accent"]))
        pdf.setFont("Helvetica-Bold", 7)
        pdf.drawString(image_box[0] + 8, image_box[1] - 16, category_label[:48])
        if image_result:
            credit = "Image credit: " + (image_result.get("creator") or "Wikimedia Commons")
            if image_result.get("license"):
                credit += " | " + image_result["license"]
            pdf.setFillColor(HexColor(theme["muted"]))
            pdf.setFont("Helvetica", 5.5)
            pdf.drawString(image_box[0] + 8, image_box[1] - 27, credit[:78])

        text_width = 350
        y = draw_wrapped_text(pdf, slide.get("heading", ""), MARGIN,
                              PAGE_H - 120, text_width,
                              cover_style if index == 0 else heading_style, 150)
        y -= 12
        y = draw_wrapped_text(pdf, slide.get("subheading", ""), MARGIN,
                              y, text_width, sub_style, 105) - 18

        bullets = clean_items(slide.get("bullets", []), 4)
        for b_index, bullet in enumerate(bullets):
            if y < 125:
                break
            y = draw_bullet(pdf, bullet, MARGIN, y, text_width, theme, b_index + 1)

        if index == 0:
            pdf.setFillColor(HexColor(theme["panel"]))
            pdf.roundRect(MARGIN, 105, 350, 62, 9, fill=1, stroke=0)
            pdf.setFillColor(HexColor(theme["text"]))
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(MARGIN + 15, 141, "CHEMSTRIDE INDUSTRY UPDATE")
            pdf.setFillColor(HexColor(theme["muted"]))
            pdf.setFont("Helvetica", 9)
            pdf.drawString(MARGIN + 15, 122, "News | Analysis | Business Perspective")

        if index == 5:
            pdf.setFillColor(HexColor(theme["muted"]))
            pdf.setFont("Helvetica-Bold", 7)
            pdf.drawString(MARGIN, 91, "ORIGINAL ARTICLE SOURCE")
            pdf.setFillColor(HexColor(theme["text"]))
            pdf.setFont("Helvetica", 8)
            pdf.drawString(MARGIN, 77, str(source_name)[:75])
            if source_url.startswith(("http://", "https://")):
                pdf.linkURL(source_url, (MARGIN, 68, PAGE_W - MARGIN, 90), relative=0)

        draw_footer(pdf, index, theme)
        pdf.showPage()

    pdf.save()
    buffer.seek(0)
    return buffer.getvalue()

def generate_carousel(news, verified_data, use_ai=True, theme_choice="Auto"):
    slides = generate_slide_content(news, verified_data, use_ai=use_ai)
    theme_name = choose_theme(news, theme_choice)
    pdf_bytes = create_pdf(slides, news, verified_data, theme_name)
    return {
        "slides": slides,
        "pdf": pdf_bytes,
        "filename": "chemstride_linkedin_carousel.pdf",
        "theme": theme_name,
        "image_category": "story-aware ChemStride vector illustrations; no unverified external images",
    }
