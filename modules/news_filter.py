
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime


# Relevant areas for ChemStride
RELEVANT_KEYWORDS = [
    "chemical",
    "chemicals",
    "petrochemical",
    "petrochemicals",
    "polymer",
    "polymers",
    "pharmaceutical",
    "raw material",
    "specialty chemicals",
    "manufacturing",
    "supply chain",
    "imports",
    "exports",
    "investment",
    "production",
    "industrial",
    "trade",
    "surfactants"
]


def parse_date(date_string):

    try:
        date = parsedate_to_datetime(date_string)

        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)

        return date

    except (TypeError, ValueError, OverflowError):
        return None


def filter_news(news_list, days=30):

    filtered_news = []

    current_time = datetime.now(timezone.utc)
    cutoff_date = current_time - timedelta(days=days)

    for news in news_list:

        published_date = parse_date(news.get("published"))

        # Remove articles with missing or invalid dates
        if published_date is None:
            continue

        # Remove outdated news
        if published_date < cutoff_date:
            continue

        content = (
            news.get("title", "") + " " +
            news.get("summary", "")
        ).lower()

        # Check industry relevance
        matching_keywords = [
            keyword
            for keyword in RELEVANT_KEYWORDS
            if keyword in content
        ]

        if matching_keywords:

            news["matched_keywords"] = matching_keywords
            filtered_news.append(news)

    return filtered_news


if __name__ == "__main__":

    from modules.news_collector import collect_news

    all_news = collect_news()

    recent_news = filter_news(all_news)

    print("\nTotal collected:", len(all_news))
    print("Recent relevant news:", len(recent_news))

    for index, news in enumerate(recent_news, 1):

        print(f"\n{index}. {news['title']}")
        print("Source:", news["source"])
        print("Published:", news["published"])
        print("Matched:", news["matched_keywords"])
