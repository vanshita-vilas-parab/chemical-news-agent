
import feedparser
import requests
import re
import time

from urllib.parse import quote, urlparse
from concurrent.futures import ThreadPoolExecutor


# --------------------------------------------------
# CHEMSTRIDE NEWS TOPICS
# --------------------------------------------------

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


# --------------------------------------------------
# TEXT CLEANING
# --------------------------------------------------

def clean_text(text):
    """Remove HTML tags and unnecessary spaces."""

    text = re.sub(r"<[^>]+>", "", text or "")
    return re.sub(r"\s+", " ", text).strip()


# --------------------------------------------------
# URL VALIDATION
# --------------------------------------------------

def is_google_news_url(url):
    """Check whether the URL belongs to Google News."""

    try:
        host = urlparse(url).netloc.lower()

        return (
            host == "news.google.com"
            or host.endswith(".news.google.com")
        )

    except Exception:
        return False


def is_valid_publisher_url(url):
    """Check whether the URL is a valid non-Google HTTP URL."""

    try:
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            return False

        if not parsed.netloc:
            return False

        if is_google_news_url(url):
            return False

        return True

    except Exception:
        return False


# --------------------------------------------------
# GOOGLE NEWS URL DECODER
# --------------------------------------------------

def resolve_article_url(url):
    """
    Convert a Google News RSS URL into the publisher URL.

    Returns an empty string if decoding fails.
    """

    if not url:
        return ""

    # Already a publisher URL.
    if not is_google_news_url(url):

        if is_valid_publisher_url(url):
            return url

        return ""

    try:

        from googlenewsdecoder import gnewsdecoder

        result = gnewsdecoder(
            url,
            interval=1,
            timeout=15
        )

        if not isinstance(result, dict):
            print("Decoder returned an unexpected response:", result)
            return ""

        # Support both current and older package response formats.
        success = (
            result.get("success") is True
            or result.get("status") is True
        )

        decoded_url = result.get("decoded_url", "")

        if success and is_valid_publisher_url(decoded_url):
            return decoded_url

        print(
            "Could not decode Google News URL:",
            result.get("message", "Unknown decoding error")
        )

        return ""

    except ImportError:
        print(
            "googlenewsdecoder is not installed. "
            "Run: pip install googlenewsdecoder"
        )
        return ""

    except Exception as error:

        print(f"Google News decoding error: {error}")
        return ""


# --------------------------------------------------
# NEWS COLLECTION
# --------------------------------------------------

def collect_news(max_results=10):

    all_news = []

    # --------------------------------------------------
    # FETCH RSS FEEDS
    # --------------------------------------------------

    for topic in NEWS_TOPICS:

        print(f"\nFetching news for: {topic}")

        rss_url = (
            "https://news.google.com/rss/search?q="
            + quote(topic)
            + "&hl=en-IN&gl=IN&ceid=IN:en"
        )

        try:

            feed = feedparser.parse(rss_url)

            for entry in feed.entries[:max_results]:

                google_url = entry.get("link", "")

                news = {
                    "title": clean_text(
                        entry.get("title", "")
                    ),

                    # Original Google News URL.
                    "link": google_url,

                    # Actual publisher URL, populated below.
                    "original_url": "",

                    "published": entry.get(
                        "published", ""
                    ),

                    "summary": clean_text(
                        entry.get("summary", "")
                    ),

                    "source": entry.get(
                        "source", {}
                    ).get("title", "Unknown"),

                    "topic": topic,

                    "url_resolution_status": "pending",

                    "url_resolution_message": ""
                }

                if news["title"] and google_url:
                    all_news.append(news)

        except Exception as error:

            print(
                f"Failed to collect topic '{topic}': {error}"
            )

    # --------------------------------------------------
    # REMOVE DUPLICATE ARTICLES
    # --------------------------------------------------

    unique_news = []
    seen_links = set()
    seen_titles = set()

    for news in all_news:

        link = news["link"]
        title = news["title"].lower()

        if link in seen_links or title in seen_titles:
            continue

        seen_links.add(link)
        seen_titles.add(title)

        unique_news.append(news)

    print(
        f"\nTotal unique articles collected: "
        f"{len(unique_news)}"
    )

    # --------------------------------------------------
    # RESOLVE PUBLISHER URLS
    # --------------------------------------------------

    print("\nResolving original publisher URLs...")

    def process_article(news):

        google_url = news["link"]

        publisher_url = resolve_article_url(google_url)

        if publisher_url:

            news["original_url"] = publisher_url
            news["url_resolution_status"] = "success"

            print(
                f"SUCCESS | {news['source']} | "
                f"{urlparse(publisher_url).netloc}"
            )

        else:

            news["url_resolution_status"] = "failed"

            news["url_resolution_message"] = (
                "Google News link could not be decoded."
            )

            print(
                f"FAILED | {news['title'][:70]}"
            )

        return news

    # Keep concurrency low to reduce Google rate limiting.
    with ThreadPoolExecutor(max_workers=2) as executor:

        unique_news = list(
            executor.map(process_article, unique_news)
        )

    # --------------------------------------------------
    # RESOLUTION SUMMARY
    # --------------------------------------------------

    resolved_count = sum(
        1 for news in unique_news
        if news["url_resolution_status"] == "success"
    )

    failed_count = len(unique_news) - resolved_count

    print("\n" + "=" * 55)
    print("NEWS COLLECTION SUMMARY")
    print("=" * 55)

    print("Total collected:", len(unique_news))
    print("Publisher URLs resolved:", resolved_count)
    print("Publisher URLs failed:", failed_count)

    if unique_news:
        print(
            "Resolution rate:",
            f"{resolved_count / len(unique_news) * 100:.1f}%"
        )

    print("=" * 55)

    return unique_news


# --------------------------------------------------
# MODULE TEST
# --------------------------------------------------

if __name__ == "__main__":

    news_list = collect_news(max_results=10)

    print("\nFINAL COLLECTED NEWS")

    for index, news in enumerate(news_list, start=1):

        print(f"\n{index}. {news['title']}")

        print("Publisher:", news["source"])

        print("Published:", news["published"])

        print("Google News URL:", news["link"])

        print(
            "Original publisher URL:",
            news["original_url"] or "Not resolved"
        )

        print(
            "Resolution status:",
            news["url_resolution_status"]
        )
