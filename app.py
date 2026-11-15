
import streamlit as st

from modules.news_collector import collect_news
from modules.news_filter import filter_news
from modules.news_ranker import rank_news
from modules.source_verifier import (
    VERIFIED_NEWS,
    get_verified_facts,
    get_sources,
    validate_news
)
from modules.article_generator import generate_article


st.set_page_config(
    page_title="ChemStride News Agent",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 ChemStride – Chemical Industry News Agent")

st.write(
    "An AI-assisted tool to discover chemical industry developments, "
    "rank relevant news, and prepare LinkedIn article drafts."
)

st.divider()


# SECTION 1: NEWS DISCOVERY

st.header("1. Chemical Industry News Discovery")

st.write(
    "Collect recent news from multiple chemical industry topics "
    "and rank the most relevant developments."
)

if st.button("Collect and Rank Latest News", type="primary"):

    with st.spinner("Collecting and ranking news..."):

        try:
            all_news = collect_news(max_results=10)
            recent_news = filter_news(all_news)
            ranked_news = rank_news(recent_news)

            st.session_state["ranked_news"] = ranked_news
            st.session_state["total_collected"] = len(all_news)
            st.session_state["total_filtered"] = len(recent_news)

        except Exception as error:
            st.error(f"News collection failed: {error}")


ranked_news = st.session_state.get("ranked_news", [])

if ranked_news:

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Articles collected",
        st.session_state.get("total_collected", 0)
    )

    col2.metric(
        "Recent relevant articles",
        st.session_state.get("total_filtered", 0)
    )

    col3.metric(
        "After duplicate removal",
        len(ranked_news)
    )

    st.subheader("Top 10 Ranked News Articles")

    for index, news in enumerate(ranked_news[:10], 1):

        with st.expander(
            f"{index}. {news['title']} — Score: {news['score']}/100"
        ):

            st.write("**Publisher:**", news.get("source", "Unknown"))
            st.write("**Published:**", news.get("published", "Unknown"))

            st.write("**Score breakdown:**")
            st.write(news["scores"])

            st.write("**Why this news was selected:**")
            for reason in news.get("selection_reasons", []):
                st.write(f"- {reason}")

            st.markdown(
                f"[Read original news article]({news['link']})"
            )

else:
    st.info("Click the button above to collect and rank the latest news.")


st.divider()


# SECTION 2: EDITORIAL SELECTION

st.header("2. Selected Industry Development")

st.subheader(VERIFIED_NEWS["title"])

st.write("**Company:**", VERIFIED_NEWS["company"])

st.write(
    """
    **Why this topic was selected**

    - It involves a major new caustic soda manufacturing facility.
    - The plant has a clearly stated annual production capacity of 220,000 metric tonnes.
    - It is a relevant development for India's chemical manufacturing sector.
    - Its location, commissioning date and key details are supported by published sources.
    """
)

st.caption(
    "Editorial selection: this topic was chosen after reviewing the ranked "
    "candidates and comparing their business relevance and available evidence."
)

st.subheader("Sources and References")

for source in get_sources():
    st.markdown(
        f"- [{source['name']}]({source['url']})"
    )


st.divider()


# SECTION 3: ARTICLE GENERATION

st.header("3. Generate ChemStride LinkedIn Article")

st.write(
    "Generate a LinkedIn article using the selected development, "
    "verified facts and ChemStride's writing style."
)

if st.button("Generate LinkedIn Article", type="primary"):

    valid, message = validate_news()

    if not valid:
        st.error(message)

    else:
        with st.spinner("Generating your LinkedIn article..."):

            news_for_prompt = {
                "title": VERIFIED_NEWS["title"],
                "source": "thyssenkrupp nucera",
                "published": "5 November 2026"
            }

            article = generate_article(
                news_for_prompt,
                get_verified_facts(),
                use_ai=True
            )

            st.session_state["generated_article"] = article


article = st.session_state.get("generated_article")

if article:

    st.subheader("Generated LinkedIn Article")

    st.markdown(article)

    st.subheader("Sources and References")

    for source in get_sources():
        st.markdown(
            f"- [{source['name']}]({source['url']})"
        )

    st.info(
        "Review the article and verify all details before publishing."
    )


st.divider()

st.caption("ChemStride Chemical Industry News Agent | Project Demonstration")
