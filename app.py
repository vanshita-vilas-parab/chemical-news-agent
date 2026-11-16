
import streamlit as st
import streamlit.components.v1 as components
import html

from modules.news_collector import collect_news
from modules.news_filter import filter_news
from modules.news_ranker import rank_news

from modules.source_verifier import (
    verify_news,
    get_verified_facts,
    get_sources,
    validate_news
)

from modules.article_generator import generate_article
from modules.carousel_generator import generate_carousel


# ==================================================
# PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="ChemStride News Agent",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 ChemStride – Chemical Industry News Agent")

st.write(
    "An AI-powered tool to discover chemical industry developments, "
    "evaluate important news, and generate LinkedIn articles and carousels."
)

st.divider()


# ==================================================
# SESSION STATE HELPERS
# ==================================================

def clear_generated_content():
    keys = [
        "selected_news",
        "verified_data",
        "candidate_evaluations",
        "generated_article",
        "generated_carousel",
        "carousel_index"
    ]

    for key in keys:
        st.session_state.pop(key, None)


def get_score(news):
    try:
        return float(news.get("score", 0))
    except (TypeError, ValueError):
        return 0.0


def get_news_url(news):
    return (
        news.get("original_url")
        or news.get("link")
        or news.get("url")
        or ""
    )


def show_sources(sources):
    if not sources:
        st.caption("No source references were returned.")
        return

    for source in sources:
        name = (
            source.get("name")
            or source.get("publisher")
            or "Original source"
        )

        url = source.get("url") or source.get("link") or ""

        if url.startswith(("http://", "https://")):
            st.markdown(f"- [{name}]({url})")
        else:
            st.write(f"- {name}")


def safe_html(value):
    return html.escape(str(value or ""))


# ==================================================
# SECTION 1: NEWS DISCOVERY AND RANKING
# ==================================================

st.header("1. Chemical Industry News Discovery")

st.write(
    "Collect recent news from multiple chemical industry topics "
    "and rank the most relevant developments."
)

if st.button("Collect and Rank Latest News", type="primary"):

    with st.spinner("Collecting and ranking chemical industry news..."):

        try:
            all_news = collect_news(max_results=10)
            recent_news = filter_news(all_news)
            ranked_news = rank_news(recent_news)

            clear_generated_content()

            st.session_state["ranked_news"] = ranked_news
            st.session_state["total_collected"] = len(all_news)
            st.session_state["total_filtered"] = len(recent_news)

            st.success("News collection and ranking completed.")

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
        "Relevant articles",
        st.session_state.get("total_filtered", 0)
    )

    col3.metric(
        "Ranked articles",
        len(ranked_news)
    )

    st.subheader("Top Ranked News Articles")

    for index, news in enumerate(ranked_news[:10], 1):

        with st.expander(
            f"{index}. {news.get('title', 'Untitled')} "
            f"— Score: {get_score(news):.2f}"
        ):

            st.write("**Publisher:**", news.get("source", "Unknown"))
            st.write("**Published:**", news.get("published", "Unknown"))

            st.write("**Score breakdown:**")
            st.write(news.get("scores", {}))

            st.write("**Ranking reasons:**")

            for reason in news.get("selection_reasons", []):
                st.write(f"- {reason}")

            if news.get("eligibility_reason"):
                st.write(
                    "**Editorial eligibility:**",
                    news["eligibility_reason"]
                )

            url = get_news_url(news)

            if url.startswith(("http://", "https://")):
                st.markdown(f"[Read original article]({url})")

else:
    st.info("Click the button above to collect and rank the latest news.")


st.divider()


# ==================================================
# SECTION 2: AUTOMATIC NEWS SELECTION
# ==================================================

st.header("2. Automatic News Selection")

st.write(
    "The agent evaluates eligible ranked stories, extracts information "
    "from their original articles, and selects the strongest candidate "
    "that passes article validation."
)

if ranked_news:

    if st.button("Select Best Story and Extract Facts", type="primary"):

        clear_generated_content()

        eligible_candidates = [
            news for news in ranked_news
            if news.get("eligible_for_selection", False)
        ]

        eligible_candidates.sort(
            key=get_score,
            reverse=True
        )

        candidates_to_check = eligible_candidates[:5]

        evaluations = []
        valid_candidates = []

        if not candidates_to_check:

            st.warning(
                "No articles passed the editorial eligibility checks. "
                "Collect fresh news or review the ranking filters."
            )

        else:

            with st.spinner(
                f"Checking {len(candidates_to_check)} eligible articles "
                "and extracting their facts..."
            ):

                for candidate in candidates_to_check:

                    title = candidate.get("title", "Untitled")

                    evaluation = {
                        "title": title,
                        "score": get_score(candidate),
                        "status": "Failed",
                        "message": "",
                        "news": candidate
                    }

                    try:
                        result = verify_news(candidate)
                        valid, message = validate_news(result)

                        evaluation["message"] = message

                        if valid:

                            evaluation["status"] = "Passed"

                            valid_candidates.append({
                                "news": candidate,
                                "result": result
                            })

                        else:
                            evaluation["status"] = "Failed"

                    except Exception as error:

                        evaluation["status"] = "Error"
                        evaluation["message"] = str(error)

                        print(
                            f"Candidate processing failed: {title}: "
                            f"{repr(error)}"
                        )

                    evaluations.append(evaluation)

            st.session_state["candidate_evaluations"] = evaluations

            if valid_candidates:

                winner = max(
                    valid_candidates,
                    key=lambda item: get_score(item["news"])
                )

                st.session_state["selected_news"] = winner["news"]
                st.session_state["verified_data"] = winner["result"]

                st.success(
                    "The agent selected the highest-scoring candidate "
                    "among the articles that passed validation."
                )

            else:

                st.error(
                    "No eligible candidate passed article validation. "
                    "Try collecting fresh news."
                )


selected_news = st.session_state.get("selected_news")
verified_data = st.session_state.get("verified_data")

candidate_evaluations = st.session_state.get(
    "candidate_evaluations", []
)


if selected_news and verified_data:

    st.subheader("🏆 Selected Winning Story")

    st.markdown(f"### {selected_news.get('title', 'Untitled')}")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Winning score",
        f"{get_score(selected_news):.2f}"
    )

    col2.metric(
        "Candidates evaluated",
        len(candidate_evaluations)
    )

    col3.metric(
        "Candidates passed",
        sum(
            1 for item in candidate_evaluations
            if item["status"] == "Passed"
        )
    )

    st.write(
        "**Publisher:**",
        selected_news.get("source", "Unknown")
    )

    st.write(
        "**Published:**",
        selected_news.get("published", "Unknown")
    )

    selected_url = get_news_url(selected_news)

    if selected_url.startswith(("http://", "https://")):
        st.markdown(f"[Read selected article]({selected_url})")

    st.subheader("Why This Story Won")

    st.write(
        "The agent compared the editorial ranking scores of the "
        "eligible candidates that passed article extraction and "
        "validation. This story had the highest score in that group."
    )

    for reason in selected_news.get("selection_reasons", []):
        st.write(f"- {reason}")

    st.write("**Winning score breakdown:**")
    st.write(selected_news.get("scores", {}))

    st.subheader("Candidate Evaluation and Comparison")

    for item in candidate_evaluations:

        candidate = item["news"]

        if get_news_url(candidate) == selected_url:
            label = "🏆 SELECTED"
        else:
            label = item["status"].upper()

        with st.expander(
            f"{label} | {item['title']} | Score: {item['score']:.2f}"
        ):

            st.write("**Extraction result:**", item["status"])

            st.write(
                "**Validation details:**",
                item["message"] or "No additional details."
            )

            difference = get_score(selected_news) - item["score"]

            st.write(
                f"**Score difference from winner:** {difference:+.2f}"
            )

            st.write("**Ranking reasons:**")

            for reason in candidate.get("selection_reasons", []):
                st.write(f"- {reason}")

    st.caption(
        "The comparison covers the eligible candidates actually evaluated. "
        "Candidates that failed article validation were not considered "
        "for the final selection."
    )

    st.divider()

    # Extracted facts

    st.subheader("Extracted Facts")

    st.write(
        "The following information was extracted from the selected "
        "original article."
    )

    if verified_data.get("verification_status"):
        st.info(verified_data["verification_status"])

    if verified_data.get("main_development"):
        st.write(
            "**Main development:**",
            verified_data["main_development"]
        )

    if verified_data.get("company"):
        st.write("**Company:**", verified_data["company"])

    if verified_data.get("location"):
        st.write("**Location:**", verified_data["location"])

    for index, fact in enumerate(
        get_verified_facts(verified_data), 1
    ):
        st.write(f"{index}. {fact}")

    if verified_data.get("important_figures"):

        st.subheader("Important Figures")

        for figure in verified_data["important_figures"]:

            if isinstance(figure, dict):
                st.write(
                    f"**{figure.get('value', '')}** — "
                    f"{figure.get('description', '')}"
                )
            else:
                st.write(f"- {figure}")

    if verified_data.get("business_implications"):

        st.subheader("Business Implications")

        for item in verified_data["business_implications"]:
            st.write(f"- {item}")

    if verified_data.get("editorial_analysis"):

        st.subheader("Editorial Analysis")
        st.write(verified_data["editorial_analysis"])

    if verified_data.get("missing_information"):

        st.warning(
            "Some information was not available in the selected article:"
        )

        for item in verified_data["missing_information"]:
            st.write(f"- {item}")

    st.subheader("Sources and References")
    show_sources(get_sources(verified_data))

    st.caption(
        "Facts are extracted from the listed article. "
        "Independent verification against additional sources "
        "is recommended before publication."
    )

elif candidate_evaluations:

    st.subheader("Candidate Evaluation Results")

    for item in candidate_evaluations:

        with st.expander(
            f"{item['status']} | {item['title']} "
            f"| Score: {item['score']:.2f}"
        ):

            st.write("**Result:**", item["status"])
            st.write("**Reason:**", item["message"])

    st.warning(
        "No candidate passed validation. Review the reasons above "
        "to identify the article extraction or validation issue."
    )

elif ranked_news:

    st.info(
        "Click 'Select Best Story and Extract Facts' to evaluate "
        "eligible articles and select the winning story."
    )


st.divider()


# ==================================================
# SECTION 3: LINKEDIN ARTICLE GENERATION
# ==================================================

st.header("3. Generate ChemStride LinkedIn Article")

st.write(
    "Generate a LinkedIn article using the selected news, "
    "extracted facts and ChemStride writing guidelines."
)

if selected_news and verified_data:

    if st.button("Generate LinkedIn Article", type="primary"):

        valid, message = validate_news(verified_data)

        if not valid:
            st.error(message)

        else:

            with st.spinner(
                "Generating LinkedIn article using Gemini..."
            ):

                try:

                    article = generate_article(
                        selected_news,
                        get_verified_facts(verified_data),
                        use_ai=True,
                        business_implications=verified_data.get(
                            "business_implications", []
                        ),
                        editorial_analysis=verified_data.get(
                            "editorial_analysis", ""
                        )
                    )

                    st.session_state["generated_article"] = article
                    st.session_state.pop("generated_carousel", None)
                    st.session_state.pop("carousel_index", None)

                except Exception as error:
                    st.error(f"Article generation failed: {error}")


article = st.session_state.get("generated_article")


if article:

    st.subheader("Generated LinkedIn Article")
    st.markdown(article)

    st.subheader("Article References")
    show_sources(get_sources(verified_data))

    st.info(
        "Review the article and check the facts before publishing."
    )

elif not selected_news:

    st.info(
        "Select a winning story before generating the article."
    )


st.divider()


# ==================================================
# SECTION 4: SIX-SLIDE LINKEDIN CAROUSEL
# ==================================================

st.header("4. Generate Six-Slide LinkedIn Carousel")

st.write(
    "Create a six-slide LinkedIn carousel from the same selected "
    "news and extracted facts used for the article."
)

if article and selected_news and verified_data:

    st.write(
        "The carousel uses the same extracted article information "
        "and ChemStride's professional writing style."
    )

    if st.button(
        "Generate 6-Slide LinkedIn Carousel",
        type="primary"
    ):

        with st.spinner(
            "Creating six carousel slides and preparing the PDF..."
        ):

            try:

                carousel = generate_carousel(
                    selected_news,
                    verified_data,
                    use_ai=True
                )

                st.session_state["generated_carousel"] = carousel
                st.session_state["carousel_index"] = 0

                st.success(
                    "Your six-slide LinkedIn carousel is ready!"
                )

            except Exception as error:
                st.error(f"Carousel generation failed: {error}")


carousel = st.session_state.get("generated_carousel")


# ==================================================
# SQUARE CAROUSEL PREVIEW
# ==================================================

if carousel:

    st.subheader("Carousel Preview")

    st.caption(
        "Preview each square slide individually. "
        "The downloaded PDF contains the same six slides."
    )

    slides = carousel.get("slides", [])

    if slides:

        current_index = st.session_state.get("carousel_index", 0)

        current_index = max(
            0,
            min(current_index, len(slides) - 1)
        )

        st.session_state["carousel_index"] = current_index

        slide = slides[current_index]

        previous_col, counter_col, next_col = st.columns([1, 2, 1])

        with previous_col:

            if st.button(
                "← Previous",
                key="carousel_previous",
                disabled=current_index == 0,
                use_container_width=True
            ):

                st.session_state["carousel_index"] = current_index - 1
                st.rerun()

        with counter_col:

            st.markdown(
                f"""
                <div style="
                    text-align:center;
                    padding-top:9px;
                    font-weight:700;
                    color:#238C8C;
                ">
                    SLIDE {current_index + 1} / {len(slides)}
                </div>
                """,
                unsafe_allow_html=True
            )

        with next_col:

            if st.button(
                "Next →",
                key="carousel_next",
                disabled=current_index == len(slides) - 1,
                use_container_width=True
            ):

                st.session_state["carousel_index"] = current_index + 1
                st.rerun()

        # --------------------------------------------------
        # Prepare square slide HTML
        # --------------------------------------------------

        is_cover = current_index == 0

        background = "#123447" if is_cover else "#F6F5EF"
        heading_color = "#FFFFFF" if is_cover else "#123447"
        muted_color = "#D8E8E9" if is_cover else "#61747B"
        accent_color = "#D6A84F" if is_cover else "#238C8C"

        heading = safe_html(slide.get("heading", ""))
        subheading = safe_html(slide.get("subheading", ""))
        footer = safe_html(slide.get("footer", "CHEMSTRIDE"))

        bullet_html = ""

        for bullet in slide.get("bullets", []):

            if not str(bullet).strip():
                continue

            bullet_html += f"""
            <div style="
                display:flex;
                align-items:flex-start;
                gap:12px;
                background:#FFFFFF;
                border-radius:10px;
                padding:12px 14px;
                margin:8px 0;
                color:#203640;
                font-size:14px;
                line-height:1.4;
                border-left:4px solid #238C8C;
            ">
                <span style="color:#238C8C;font-weight:bold;">●</span>
                <span>{safe_html(bullet)}</span>
            </div>
            """

        cover_visual = ""

        if is_cover:

            cover_visual = """
            <div style="
                background:#1D4B60;
                border-radius:14px;
                padding:20px;
                margin-top:auto;
                color:#FFFFFF;
            ">
                <div style="
                    width:42px;
                    height:4px;
                    background:#D6A84F;
                    border-radius:4px;
                    margin-bottom:18px;
                "></div>

                <div style="
                    font-size:18px;
                    font-weight:700;
                    margin-bottom:10px;
                ">
                    CHEMICAL INDUSTRY
                </div>

                <div style="color:#D8E8E9;font-size:13px;">
                    News · Analysis · Business Perspective
                </div>
            </div>
            """

        preview_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                padding: 0;
                font-family: Arial, Helvetica, sans-serif;
                background: transparent;
            }}

            .slide {{
                width: 100%;
                max-width: 720px;
                aspect-ratio: 1 / 1;
                margin: 0 auto;
                padding: 5.5%;
                background: {background};
                border: 1px solid #DCE4E2;
                border-radius: 16px;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }}

            .top {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                color: {heading_color};
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 2px;
            }}

            .accent {{
                width: 48px;
                height: 4px;
                background: {accent_color};
                border-radius: 4px;
                margin-top: 13px;
                margin-bottom: 20px;
            }}

            .section {{
                color: {accent_color};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1.5px;
                margin-bottom: 15px;
            }}

            .heading {{
                color: {heading_color};
                font-size: clamp(22px, 4vw, 34px);
                line-height: 1.13;
                font-weight: 750;
                margin-bottom: 15px;
                overflow-wrap: anywhere;
            }}

            .subheading {{
                color: {muted_color};
                font-size: 15px;
                line-height: 1.45;
                margin-bottom: 15px;
                overflow-wrap: anywhere;
            }}

            .content {{
                flex: 1;
                min-height: 0;
                overflow: hidden;
            }}

            .bottom {{
                border-top: 1px solid {'#416273' if is_cover else '#DCE4E2'};
                margin-top: 12px;
                padding-top: 10px;
                display: flex;
                justify-content: space-between;
                color: {muted_color};
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
        </style>
        </head>

        <body>
            <div class="slide">

                <div class="top">
                    <span>CHEMSTRIDE</span>
                    <span style="font-weight:400;letter-spacing:1px;">
                        INDUSTRY INSIGHTS
                    </span>
                </div>

                <div class="accent"></div>

                <div class="section">{footer}</div>

                <div class="heading">{heading}</div>

                <div class="subheading">{subheading}</div>

                <div class="content">
                    {bullet_html}
                    {cover_visual}
                </div>

                <div class="bottom">
                    <span>CHEMSTRIDE</span>
                    <span>{current_index + 1:02d} / 06</span>
                </div>

            </div>
        </body>
        </html>
        """

        # Render HTML in a component iframe instead of Markdown.
        components.html(
            preview_html,
            height=760,
            scrolling=False
        )

        st.divider()

        pdf_bytes = carousel.get("pdf")

        if pdf_bytes:

            st.download_button(
                label="Download LinkedIn Carousel (PDF)",
                data=pdf_bytes,
                file_name=carousel.get(
                    "filename",
                    "chemstride_linkedin_carousel.pdf"
                ),
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )

        st.subheader("Carousel References")
        show_sources(get_sources(verified_data))

        st.info(
            "Review the six slides and their source references "
            "before publishing."
        )

else:

    if article:
        st.info(
            "Your article is ready. Click the button above to generate "
            "the six-slide LinkedIn carousel."
        )

    else:
        st.info(
            "Generate the LinkedIn article first to enable carousel generation."
        )


# ==================================================
# FOOTER
# ==================================================

st.divider()

st.caption(
    "ChemStride Chemical Industry News Agent | "
    "AI-Assisted News Research and LinkedIn Content Generation"
)
