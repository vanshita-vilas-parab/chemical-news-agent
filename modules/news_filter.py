
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime


# --------------------------------------------------
# 1. RELEVANT INDUSTRY KEYWORDS
# --------------------------------------------------

RELEVANT_KEYWORDS = [
    "chemical",
    "chemicals",
    "petrochemical",
    "petrochemicals",
    "specialty chemicals",
    "speciality chemicals",
    "chlor alkali",
    "caustic soda",
    "chlorine",
    "industrial chemicals",
    "polymer",
    "polymers",
    "plastics",
    "pharmaceutical",
    "pharmaceutical raw materials",
    "pharma intermediates",
    "active pharmaceutical ingredient",
    "api manufacturing",
    "agrochemical",
    "agrochemicals",
    "pesticides",
    "chemical feedstock",
    "chemical raw material",
    "chemical manufacturing",
    "chemical production",
    "chemical plant",
    "chemical imports",
    "chemical exports",
    "chemical supply chain",
    "surfactants",
    "solvents",
    "resins",
    "fertilizers",
    "synthetic chemicals",
    "chemical precursors"
]


# --------------------------------------------------
# 2. DATE PARSER
# --------------------------------------------------

def parse_date(date_string):

    if not date_string:
        return None

    try:
        date = parsedate_to_datetime(date_string)

        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        return date.astimezone(timezone.utc)

    except (TypeError, ValueError, OverflowError):
        return None


# --------------------------------------------------
# 3. NEWS FILTER
# --------------------------------------------------

def filter_news(news_list, days=30):

    filtered_news = []

    current_time = datetime.now(timezone.utc)
    cutoff_date = current_time - timedelta(days=days)

    for news in news_list:

        published_date = parse_date(
            news.get("published")
        )

        # Reject missing or invalid dates.
        if published_date is None:
            continue

        # Reject outdated articles.
        if published_date < cutoff_date:
            continue

        # Reject future-dated articles.
        if published_date > current_time:
            continue

        title = str(
            news.get("title", "") or ""
        )

        summary = str(
            news.get("summary", "") or ""
        )

        content = (title + " " + summary).lower()

        # Find relevant industry keywords.
        matching_keywords = [
            keyword
            for keyword in RELEVANT_KEYWORDS
            if keyword in content
        ]

        if matching_keywords:

            # Copy the record instead of modifying
            # the original collected news.
            news_copy = news.copy()

            news_copy["matched_keywords"] = (
                matching_keywords
            )

            news_copy["published_datetime"] = (
                published_date.isoformat()
            )

            filtered_news.append(news_copy)

    return filtered_news


# --------------------------------------------------
# 4. TEST FILTER
# --------------------------------------------------

if __name__ == "__main__":

    from modules.news_collector import collect_news

    all_news = collect_news()

    recent_news = filter_news(
        all_news,
        days=30
    )

    print("\nCHEMSTRIDE NEWS FILTER")

    print("Total collected:", len(all_news))
    print("Recent relevant news:", len(recent_news))

    for index, news in enumerate(recent_news, 1):

        print(f"\n{index}. {news.get('title', 'Untitled')}")
        print("Source:", news.get("source", "Unknown"))
        print("Published:", news.get("published", "Unknown"))
        print("Matched:", news.get("matched_keywords", []))
