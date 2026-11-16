
from datetime import datetime, timezone
from difflib import SequenceMatcher

from modules.news_filter import parse_date


# --------------------------------------------------
# 1. CHEMICAL INDUSTRY KEYWORDS
# --------------------------------------------------

BUSINESS_AREAS = {
    "chemicals": [
        "chemical industry", "chemical manufacturer",
        "chemical manufacturing", "chemicals",
        "petrochemical", "petrochemicals",
        "specialty chemical", "specialty chemicals",
        "chlor alkali", "caustic soda", "chlorine",
        "solvent", "surfactant", "fertilizer",
        "industrial chemicals", "chemical plant"
    ],

    "polymers": [
        "polymer", "polymers", "plastics",
        "rubber", "resin", "polyethylene",
        "polypropylene", "polyvinyl chloride",
        "pvc", "polymer manufacturing"
    ],

    "pharma": [
        "pharmaceutical", "pharma",
        "active pharmaceutical ingredient",
        "pharmaceutical raw material",
        "pharma intermediate", "api manufacturing"
    ],

    "agrochemicals": [
        "agrochemical", "agrochemicals",
        "pesticide", "pesticides",
        "crop protection", "herbicide",
        "insecticide", "fungicide"
    ],

    "trade": [
        "chemical imports", "chemical exports",
        "chemical import", "chemical export",
        "chemical supply chain", "chemical feedstock",
        "chemical raw material", "chemical tariff"
    ],

    "food": [
        "food ingredients", "food ingredient",
        "food additives", "food chemicals"
    ]
}


# Core terms used to determine whether a story
# is genuinely connected to the chemical industry.

CORE_INDUSTRY_KEYWORDS = [
    "chemical industry",
    "chemical manufacturer",
    "chemical manufacturing",
    "chemical plant",
    "chemical production",
    "chemical sector",
    "chemicals industry",
    "chemical products",
    "petrochemical",
    "petrochemicals",
    "specialty chemicals",
    "specialty chemical",
    "speciality chemicals",
    "speciality chemical",
    "chlor alkali",
    "caustic soda",
    "chlorine",
    "polymer manufacturing",
    "polymer industry",
    "agrochemical",
    "agrochemicals",
    "chemical feedstock",
    "chemical raw material",
    "pharmaceutical raw material",
    "api manufacturing",
    "industrial chemicals",
    "chemical imports",
    "chemical exports",
    "coal-based chemicals",
    "chemicals and petrochemicals"
]


# --------------------------------------------------
# 2. INDUSTRY DEVELOPMENT KEYWORDS
# --------------------------------------------------

STRONG_DEVELOPMENTS = [
    "new plant",
    "new facility",
    "new factory",
    "manufacturing facility",
    "manufacturing plant",
    "production facility",
    "manufacturing unit",
    "production unit",
    "plant commissioned",
    "commissioned",
    "commissioning",
    "capacity expansion",
    "production capacity",
    "factory expansion",
    "manufacturing expansion",
    "construction begins",
    "breaks ground",
    "new production line",
    "starts production",
    "commercial production",
    "launches production",
    "acquisition",
    "joint venture",
    "strategic partnership",
    "signs partnership",
    "product launch",
    "launches new product",
    "enters new market",
    "opens new facility",
    "starts a new unit",
    "tests new platform",
    "productivity gain",
    "unveils new platform",
    "new technology",
    "capacity addition",
    "sets up facility",
    "establishes manufacturing"
]


OTHER_DEVELOPMENTS = [
    "investment",
    "invests",
    "invested",
    "investment plan",
    "investment commitment",
    "manufacturing push",
    "expansion plan",
    "supply agreement",
    "long-term agreement",
    "export agreement",
    "import restriction",
    "trade agreement",
    "policy change",
    "government approval",
    "project approval",
    "regulatory approval",
    "production target",
    "production increase",
    "supply contract",
    "new regulation",
    "duty imposed",
    "import duty",
    "export duty",

    "identifies priority",
    "priority chemicals",
    "government initiative",
    "new policy",
    "policy initiative",
    "announces scheme",
    "launches scheme",
    "approves project",
    "approves investment",
    "proposes investment",
    "sets target",
    "announces target",
    "regulatory framework",
    "new guidelines",
    "import dependence",
    "reduce import dependence",
    "reduces import dependence",
    "import substitution",
    "financial results",
    "quarterly results",
    "reports revenue",
    "reports profit",
    "profit declines",
    "profit increases",
    "revenue growth",
    "revenue declines",
    "pat drops",
    "pat declines",
    "net profit declines",
    "net profit drops",
    "profit declines",
    "profit drops",
    "earnings decline",
    "earnings drop",
    "self-reliance",
    "self reliance",
    "domestic self-reliance",
    "raw material independence",
    "pharmaceutical self-reliance",
]


# --------------------------------------------------
# 3. BUSINESS IMPACT KEYWORDS
# --------------------------------------------------

IMPACT_KEYWORDS = [
    "domestic production",
    "supply shortage",
    "supply disruption",
    "import substitution",
    "import restriction",
    "export growth",
    "raw material supply",
    "new market",
    "market access",
    "production capacity",
    "industrial demand",
    "sourcing",
    "manufacturing growth",
    "trade agreement",
    "supply chain diversification",
    "reduced imports",
    "local production",
    "capacity addition",
    "supply security",
    "feedstock availability",
    "production costs",
    "chemical exports",
    "chemical imports",
    "import dependence",
    "reduce import dependence",
    "reduces import dependence",
    "priority chemicals",
    "coal-based chemicals",
    "domestic manufacturing",
    "chemical production",
    "chemical industry growth",
    "speciality chemicals",
    "specialty chemicals",
    "pharmaceutical intermediates",
    "profit decline",
    "earnings decline",
    "financial performance",
    "pharmaceutical raw materials",
    "raw material independence",
    "domestic self-reliance",
    "pharmaceutical manufacturing",
]


# --------------------------------------------------
# 4. EDITORIAL PENALTIES
# --------------------------------------------------

NEGATIVE_KEYWORDS = [
    "fire at",
    "factory fire",
    "massive fire",
    "explosion",
    "chemical leak",
    "industrial accident",
    "fatalities",
    "workers injured",
    "opioid crisis",
    "drug trafficking",
    "illegal drug",
    "criminal network",
    "fraud",
    "pollution incident"
]


STOCK_KEYWORDS = [
    "stock recommendation",
    "stock price",
    "share price",
    "top stocks",
    "price target",
    "buy or sell",
    "investor portfolio"
]


GENERIC_REPORT_KEYWORDS = [
    "market size",
    "growth forecast",
    "market forecast",
    "market outlook",
    "market research report",
    "cagr",
    "market analysis report",
    "market to 2035",
    "market to 2040",
    "industry outlook",
    "industry forecast",
    "through 2035",
    "through 2040",
    "set for growth",
    "eyes massive expansion",
    "growth opportunities",
    "market set for growth"
]


LOW_VALUE_KEYWORDS = [
    "receives award",
    "wins award",
    "award ceremony",
    "honoured with",
    "honored with",
    "medal",
    "appoints new ceo",
    "new ceo appointed",
    "receives international medal",
    "industry award",
    "leadership award"
]


# --------------------------------------------------
# 5. HELPER FUNCTIONS
# --------------------------------------------------

def find_matches(content, keywords):
    """Return all matching keywords."""
    content = content.lower()

    return [
        keyword for keyword in keywords
        if keyword in content
    ]


def get_news_content(news):
    """Combine headline and summary for scoring."""
    title = str(news.get("title", "") or "").lower()
    summary = str(news.get("summary", "") or "").lower()

    return title, summary, title + " " + summary


# --------------------------------------------------
# 6. CHEMICAL INDUSTRY ELIGIBILITY
# --------------------------------------------------


def check_editorial_eligibility(
    content,
    matched_categories,
    development_score,
    impact_score
):
    """
    Check direct chemical-industry relevance and
    meaningful business or policy development.
    """

    core_matches = find_matches(
        content,
        CORE_INDUSTRY_KEYWORDS
    )

    if not core_matches:
        return (
            False,
            "No clear chemical-industry connection.",
            core_matches
        )

    # Company performance and policy developments
    # can be relevant even without plant expansion.

    special_development_signals = [
        "identifies priority",
        "priority chemicals",
        "government initiative",
        "new policy",
        "policy initiative",
        "import dependence",
        "financial results",
        "quarterly results",
        "reports revenue",
        "reports profit",
        "approves project",
        "sets target",
        "pat drops",
        "pat declines",
        "net profit declines",
        "net profit drops",
        "profit declines",
        "profit drops",
        "earnings decline",
        "earnings drop",
        "self-reliance",
        "self reliance",
        "raw material independence",
    ]

    special_matches = find_matches(
        content,
        special_development_signals
    )

    has_business_signal = (
        development_score >= 8
        or impact_score >= 6
        or bool(special_matches)
    )

    if not has_business_signal:
        return (
            False,
            "Chemical-industry relevance found, but "
            "no sufficiently concrete business, policy "
            "or operational development was identified.",
            core_matches
        )

    return (
        True,
        "Direct chemical-industry relevance and a "
        "meaningful business or policy development were identified.",
        core_matches
    )



# --------------------------------------------------
# 7. CALCULATE NEWS SCORE
# --------------------------------------------------

def calculate_scores(news):

    title, summary, content = get_news_content(news)

    # 1. Business relevance: maximum 25 points

    matched_categories = []

    for category, keywords in BUSINESS_AREAS.items():

        if any(keyword in content for keyword in keywords):
            matched_categories.append(category)

    relevance_score = min(
        len(matched_categories) * 5,
        25
    )

    # 2. Specific business development: maximum 40

    strong_matches = find_matches(
        content,
        STRONG_DEVELOPMENTS
    )

    other_matches = find_matches(
        content,
        OTHER_DEVELOPMENTS
    )

    title_strong_matches = find_matches(
        title,
        STRONG_DEVELOPMENTS
    )

    development_score = min(
        len(strong_matches) * 8
        + len(title_strong_matches) * 4
        + len(other_matches) * 4,
        40
    )

    # Generic investment references alone should
    # not receive the same priority as confirmed projects.

    investment_context = [
        "announces",
        "announced",
        "plans",
        "planned",
        "commits",
        "committed",
        "invests",
        "invested",
        "will invest",
        "identifies",
        "approves",
        "approved",
        "proposes",
        "proposed",
        "launches",
        "launched"
    ]

    if (
        "investment" in other_matches
        and not any(word in content for word in investment_context)
    ):
        development_score = max(
            0,
            development_score - 4
        )

    # 3. Business impact: maximum 15

    impact_matches = find_matches(
        content,
        IMPACT_KEYWORDS
    )

    impact_score = min(
        len(impact_matches) * 3,
        15
    )

    # 4. Recency: maximum 15

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
        content,
        NEGATIVE_KEYWORDS
    )

    stock_matches = find_matches(
        content,
        STOCK_KEYWORDS
    )

    generic_matches = find_matches(
        content,
        GENERIC_REPORT_KEYWORDS
    )

    low_value_matches = find_matches(
        content,
        LOW_VALUE_KEYWORDS
    )

    penalty = 0

    if negative_matches:

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

    # 6. Specificity bonus: maximum 5

    specific_indicators = [
        "tonnes",
        "metric tonnes",
        "million",
        "capacity",
        "billion",
        "crore",
        "commissioned",
        "production line",
        "plant",
        "facility"
    ]

    specificity_score = 0

    if any(
        word in content
        for word in specific_indicators
    ):
        specificity_score = 5

    # 7. Total score

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

    # 8. Editorial eligibility

    eligible, eligibility_reason, core_matches = (
        check_editorial_eligibility(
            content,
            matched_categories,
            development_score,
            impact_score
        )
    )

    # Exclude unsuitable content from editorial selection.

    if negative_matches and not (
        impact_matches and (
            "supply disruption" in content
            or "production halted" in content
            or "production shutdown" in content
        )
    ):
        eligible = False
        eligibility_reason = (
            "Excluded due to an unsuitable incident-focused story."
        )

    if stock_matches:
        eligible = False
        eligibility_reason = (
            "Excluded because the story is primarily stock-focused."
        )

    if generic_matches and not strong_matches:
        eligible = False
        eligibility_reason = (
            "Generic market report without a specific development."
        )

    # 9. Explain the score

    reasons = []

    if matched_categories:
        reasons.append(
            "Relevant business areas: "
            + ", ".join(matched_categories)
        )

    if core_matches:
        reasons.append(
            "Chemical-industry connection: "
            + ", ".join(core_matches[:4])
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

    if not eligible:
        reasons.append(
            "Not eligible: " + eligibility_reason
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
        "impact_matches": impact_matches,
        "core_industry_matches": core_matches,

        "eligible_for_selection": eligible,
        "eligibility_reason": eligibility_reason,

        "reasons": reasons
    }


# --------------------------------------------------
# 8. REMOVE DUPLICATE NEWS
# --------------------------------------------------

def remove_similar_news(news_list, threshold=0.85):

    unique_news = []

    for news in news_list:

        current_title = str(
            news.get("title", "") or ""
        ).lower()

        duplicate = False

        for existing in unique_news:

            existing_title = str(
                existing.get("title", "") or ""
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


# --------------------------------------------------
# 9. RANK NEWS
# --------------------------------------------------

def rank_news(news_list):

    unique_news = remove_similar_news(news_list)

    ranked_news = []

    for news in unique_news:

        # Avoid modifying the original collected record.
        news = news.copy()

        scores = calculate_scores(news)

        news["scores"] = scores
        news["score"] = scores["total"]
        news["selection_reasons"] = scores["reasons"]

        news["eligible_for_selection"] = (
            scores["eligible_for_selection"]
        )

        news["eligibility_reason"] = (
            scores["eligibility_reason"]
        )

        ranked_news.append(news)

    ranked_news.sort(
        key=lambda item: (
            item["score"],
            str(item.get("published", ""))
        ),
        reverse=True
    )

    return ranked_news


# --------------------------------------------------
# 10. TEST THE RANKING MODULE
# --------------------------------------------------

if __name__ == "__main__":

    from modules.news_collector import collect_news
    from modules.news_filter import filter_news

    all_news = collect_news()
    filtered_news = filter_news(all_news)
    ranked_news = rank_news(filtered_news)

    eligible_news = [
        news for news in ranked_news
        if news["eligible_for_selection"]
    ]

    rejected_news = [
        news for news in ranked_news
        if not news["eligible_for_selection"]
    ]

    print("\nCHEMSTRIDE EDITORIAL NEWS RANKING")

    print("Total collected:", len(all_news))
    print("After filtering:", len(filtered_news))
    print("After duplicate removal:", len(ranked_news))
    print("Eligible stories:", len(eligible_news))
    print("Rejected stories:", len(rejected_news))

    print("\nTOP 10 ELIGIBLE DEVELOPMENTS")

    for index, news in enumerate(eligible_news[:10], 1):

        print(f"\n{index}. {news['title']}")
        print("Publisher:", news.get("source", "Unknown"))
        print("Published:", news.get("published", "Date unavailable"))
        print("Score:", news["score"], "/ 100")
        print("Score breakdown:", news["scores"])

        print("Selection reasons:")

        for reason in news["selection_reasons"]:
            print("-", reason)

        print("Link:", news.get("link", ""))

    print("\nTOP 5 REJECTED STORIES")

    for news in rejected_news[:5]:

        print("\n", news.get("title", "Untitled"))
        print("Reason:", news["eligibility_reason"])
