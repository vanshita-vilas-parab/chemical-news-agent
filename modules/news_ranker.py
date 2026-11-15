
from datetime import datetime, timezone
from difflib import SequenceMatcher

from modules.news_filter import parse_date


# ChemStride business categories
BUSINESS_AREAS = {
    "chemicals": [
        "chemical", "chemicals", "petrochemical",
        "petrochemicals", "specialty chemical",
        "specialty chemicals", "chlor alkali",
        "caustic soda", "solvent", "surfactant"
    ],
    "polymers": [
        "polymer", "polymers", "plastics",
        "rubber", "resin", "polyethylene",
        "polypropylene"
    ],
    "pharma": [
        "pharmaceutical", "pharma", "api",
        "active pharmaceutical ingredient",
        "raw material", "intermediate"
    ],
    "trade": [
        "import", "imports", "export", "exports",
        "tariff", "global sourcing", "supply chain"
    ],
    "food": [
        "food ingredient", "food ingredients",
        "food additives"
    ]
}


# Strong, specific business developments
STRONG_DEVELOPMENTS = [
    "new plant", "new facility", "new factory",
    "manufacturing facility", "manufacturing plant",
    "production facility", "manufacturing unit",
    "production unit", "plant commissioned",
    "commissioned", "commissioning",
    "capacity expansion", "production capacity",
    "factory expansion", "manufacturing expansion",
    "construction begins", "breaks ground",
    "new production line", "starts production",
    "commercial production", "launches production",
    "acquisition", "joint venture",
    "strategic partnership", "signs partnership",
    "product launch", "launches new product",
    "enters new market", "opens new facility"
    "starts a new unit",
    "starts one of",
    "tests new platform",
    "productivity gain",
    "unveils new platform",
    "new technology",
    "capacity addition",
    "sets up facility",
    "establishes manufacturing"
]

# Other developments that need stronger context
OTHER_DEVELOPMENTS = [
    "investment", "invests", "invested",
    "investment plan", "investment commitment",
    "manufacturing push", "expansion plan",
    "supply agreement", "long-term agreement",
    "export agreement", "import restriction",
    "trade agreement", "policy change",
    "government approval", "project approval"
]

# Business and supply-chain impact
IMPACT_KEYWORDS = [
    "domestic production", "supply shortage",
    "supply disruption", "import substitution",
    "import restriction", "export growth",
    "raw material supply", "new market",
    "market access", "production capacity",
    "industrial demand", "sourcing",
    "manufacturing growth", "trade agreement",
    "supply chain diversification",
    "reduced imports", "local production",
    "capacity addition", "supply security"
]

# Lower-priority or unsuitable news
NEGATIVE_KEYWORDS = [
    "fire at", "factory fire", "massive fire",
    "explosion", "chemical leak",
    "industrial accident", "fatalities",
    "workers injured", "opioid crisis",
    "drug trafficking", "illegal drug",
    "criminal network", "fraud",
    "pollution incident"
]

STOCK_KEYWORDS = [
    "stock recommendation", "stock price",
    "share price", "top stocks",
    "price target", "buy or sell",
    "investor portfolio"
]

GENERIC_REPORT_KEYWORDS = [
    "market size", "growth forecast",
    "market forecast", "market outlook",
    "market research report", "cagr",
    "market analysis report",
    "market to 2035", "market to 2040",
    "industry outlook", "industry forecast"
    "through 2035",
    "through 2040",
    "set for growth",
    "eyes massive expansion",
    "growth opportunities",
    "market set for growth"
]

LOW_VALUE_KEYWORDS = [
    "receives award", "wins award",
    "award ceremony", "honoured with",
    "honored with", "medal",
    "appoints new ceo", "new ceo appointed"
    "receives international medal",
    "industry award",
    "leadership award"
]


def find_matches(content, keywords):
    return [
        keyword for keyword in keywords
        if keyword in content
    ]


def calculate_scores(news):

    title = news.get("title", "").lower()
    summary = news.get("summary", "").lower()
    content = title + " " + summary

    # 1. Business relevance: maximum 25 points
    matched_categories = []

    for category, keywords in BUSINESS_AREAS.items():
        if any(keyword in content for keyword in keywords):
            matched_categories.append(category)

    relevance_score = min(
        len(matched_categories) * 5,
        25
    )

    # 2. Specific business development: maximum 40 points
    strong_matches = find_matches(
        content, STRONG_DEVELOPMENTS
    )

    other_matches = find_matches(
        content, OTHER_DEVELOPMENTS
    )

    title_strong_matches = find_matches(
        title, STRONG_DEVELOPMENTS
    )

    development_score = min(
        len(strong_matches) * 8
        + len(title_strong_matches) * 4
        + len(other_matches) * 4,
        40
    )

    # Generic investment references alone should not
    # receive the same priority as confirmed projects.
    if "investment" in other_matches and not any(
        word in content for word in [
            "announces", "announced", "plans",
            "planned", "commits", "committed",
            "invests", "invested", "will invest"
        ]
    ):
        development_score = max(
            0, development_score - 4
        )

    # 3. Business impact: maximum 15 points
    impact_matches = find_matches(
        content, IMPACT_KEYWORDS
    )

    impact_score = min(
        len(impact_matches) * 3,
        15
    )

    # 4. Recency: maximum 15 points
    published_date = parse_date(
        news.get("published")
    )

    recency_score = 0
    age = None

    if published_date:
        if published_date.tzinfo is None:
            published_date = published_date.replace(
                tzinfo=timezone.utc
            )

        age = (
            datetime.now(timezone.utc) - published_date
        ).total_seconds() / 86400

        if 0 <= age <= 30:
            recency_score = max(
                0,
                15 * (1 - age / 30)
            )

    # 5. Editorial penalties
    negative_matches = find_matches(
        content, NEGATIVE_KEYWORDS
    )

    stock_matches = find_matches(
        content, STOCK_KEYWORDS
    )

    generic_matches = find_matches(
        content, GENERIC_REPORT_KEYWORDS
    )

    low_value_matches = find_matches(
        content, LOW_VALUE_KEYWORDS
    )

    penalty = 0

    if negative_matches:
        # A major supply-chain or production impact
        # may still make an incident worth covering.
        if impact_matches and (
            "supply disruption" in content
            or "production halted" in content
            or "production shutdown" in content
        ):
            penalty += 12
        else:
            penalty += 30

    if stock_matches:
        penalty += 25

    if generic_matches:
        penalty += 20

    if low_value_matches:
        penalty += 18

    # 6. Specificity bonus: maximum 5 points
    specificity_score = 0

    specific_indicators = [
        "tonnes", "metric tonnes", "million",
        "capacity", "billion", "crore",
        "commissioned", "production line",
        "plant", "facility"
    ]

    if any(word in content for word in specific_indicators):
        specificity_score = 5

    total_score = max(
        0,
        min(
            100,
            relevance_score
            + development_score
            + impact_score
            + recency_score
            + specificity_score
            - penalty
        )
    )

    # Explain the ranking decision
    reasons = []

    if matched_categories:
        reasons.append(
            "Relevant business areas: "
            + ", ".join(matched_categories)
        )

    if strong_matches:
        reasons.append(
            "Specific industry development: "
            + ", ".join(strong_matches[:4])
        )

    if other_matches:
        reasons.append(
            "Additional development signals: "
            + ", ".join(other_matches[:3])
        )

    if impact_matches:
        reasons.append(
            "Business impact: "
            + ", ".join(impact_matches[:4])
        )

    if specificity_score:
        reasons.append(
            "Contains specific operational or capacity details"
        )

    if generic_matches:
        reasons.append(
            "Penalized: generic market forecast or report"
        )

    if negative_matches:
        reasons.append(
            "Penalized: negative incident or crisis reporting"
        )

    if stock_matches:
        reasons.append(
            "Penalized: stock-focused news"
        )

    if low_value_matches:
        reasons.append(
            "Penalized: award or individual announcement"
        )

    if not reasons:
        reasons.append(
            "Limited direct business relevance"
        )

    return {
        "relevance": round(relevance_score, 2),
        "development": round(development_score, 2),
        "impact": round(impact_score, 2),
        "recency": round(recency_score, 2),
        "specificity": specificity_score,
        "penalty": penalty,
        "total": round(total_score, 2),
        "matched_categories": matched_categories,
        "development_matches": (
            strong_matches + other_matches
        ),
        "reasons": reasons
    }


def remove_similar_news(news_list, threshold=0.85):

    unique_news = []

    for news in news_list:

        current_title = news.get(
            "title", ""
        ).lower()

        duplicate = False

        for existing in unique_news:

            existing_title = existing.get(
                "title", ""
            ).lower()

            similarity = SequenceMatcher(
                None,
                current_title,
                existing_title
            ).ratio()

            if similarity >= threshold:
                duplicate = True
                break

        if not duplicate:
            unique_news.append(news)

    return unique_news


def rank_news(news_list):

    unique_news = remove_similar_news(news_list)

    ranked_news = []

    for news in unique_news:

        scores = calculate_scores(news)

        news["scores"] = scores
        news["score"] = scores["total"]
        news["selection_reasons"] = scores["reasons"]

        ranked_news.append(news)

    ranked_news.sort(
        key=lambda item: (
            item["score"],
            item.get("published", "")
        ),
        reverse=True
    )

    return ranked_news


if __name__ == "__main__":

    from modules.news_collector import collect_news
    from modules.news_filter import filter_news

    all_news = collect_news()
    filtered_news = filter_news(all_news)
    ranked_news = rank_news(filtered_news)

    print("\nCHEMSTRIDE EDITORIAL NEWS RANKING")

    print("Total collected:", len(all_news))
    print("After filtering:", len(filtered_news))
    print("After duplicate removal:", len(ranked_news))

    print("\nTOP 10 DEVELOPMENTS")

    for index, news in enumerate(ranked_news[:10], 1):

        print(f"\n{index}. {news['title']}")
        print("Publisher:", news.get("source", "Unknown"))
        print("Published:", news.get("published", "Date unavailable"))
        print("Score:", news["score"], "/ 100")
        print("Score breakdown:", news["scores"])

        print("Selection reasons:")

        for reason in news["selection_reasons"]:
            print("-", reason)

        print("Link:", news.get("link", ""))
