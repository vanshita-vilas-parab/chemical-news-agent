
import feedparser
from urllib.parse import quote
from datetime import datetime, timezone
import re


# Topics relevant to ChemStride
NEWS_TOPICS = [
    "chemical industry India",
    "global chemical industry",
    "specialty chemicals manufacturing",
    "pharmaceutical raw materials industry",
    "polymer industry",
    "chemical imports exports India",
    "chemical supply chain",
    "chemical industry investments"
]


def clean_text(text):
    """Remove HTML tags and unnecessary spaces."""

    text = re.sub(r"<[^>]+>", "", text or "")
    return re.sub(r"\s+", " ", text).strip()


def collect_news(max_results=10):

    all_news = []

    for topic in NEWS_TOPICS:

        print(f"Fetching news for: {topic}")

        rss_url = (
            "https://news.google.com/rss/search?q="
            + quote(topic)
            + "&hl=en-IN&gl=IN&ceid=IN:en"
        )

        feed = feedparser.parse(rss_url)

        for entry in feed.entries[:max_results]:

            news = {
                "title": clean_text(entry.get("title", "")),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "summary": clean_text(
                    entry.get("summary", "")
                ),
                "source": entry.get("source", {}).get(
                    "title", "Unknown"
                ),
                "topic": topic
            }

            if news["title"] and news["link"]:
                all_news.append(news)

    # Remove duplicate articles
    unique_news = []
    seen_links = set()

    for news in all_news:

        if news["link"] not in seen_links:
            seen_links.add(news["link"])
            unique_news.append(news)

    return unique_news


if __name__ == "__main__":

    news_list = collect_news()

    print("\nTotal unique news collected:", len(news_list))

    for index, news in enumerate(news_list, start=1):

        print(f"\n{index}. {news['title']}")
        print("Source:", news["source"])
        print("Published:", news["published"])
        print("Link:", news["link"])
