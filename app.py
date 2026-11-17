import streamlit as st
import streamlit.components.v1 as components

try:
    import fitz  # PyMuPDF: renders each PDF page as an image for reliable preview
except ImportError:
    fitz = None

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


# PAGE CONFIGURATION

st.set_page_config(
    page_title="ChemStride News Agent",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 ChemStride – Chemical Industry News Agent")

st.write(
    "An AI-powered tool to discover chemical industry developments, "
    "select important news, and generate LinkedIn articles and carousels."
)

st.divider()


# SECTION 1: NEWS DISCOVERY AND RANKING

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

            st.session_state["ranked_news"] = ranked_news
            st.session_state["total_collected"] = len(all_news)
            st.session_state["total_filtered"] = len(recent_news)

            # Clear previous generated content
            for key in [
                "selected_news",
                "verified_data",
                "generated_article",
                "generated_carousel"
            ]:
                st.session_state.pop(key, None)

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

    st.subheader("Top 10 Ranked News Articles")

    for index, news in enumerate(ranked_news[:10], 1):

        with st.expander(
            f"{index}. {news.get('title', 'Untitled')} "
            f"— Score: {news.get('score', 0)}/100"
        ):

            st.write("**Publisher:**", news.get("source", "Unknown"))

            st.write("**Published:**", news.get("published", "Unknown"))

            st.write("**Score breakdown:**")
            st.write(news.get("scores", {}))

            st.write("**Ranking reasons:**")

            for reason in news.get("selection_reasons", []):
                st.write(f"- {reason}")

            if news.get("link"):
                st.markdown(
                    f"[Read original article]({news['link']})"
                )

else:
    st.info("Click the button above to collect and rank the latest news.")


st.divider()


# SECTION 2: AUTOMATIC NEWS SELECTION

st.header("2. Automatic News Selection")

st.write(
    "The agent evaluates the ranked news and selects the highest-ranked "
    "suitable story from the collected articles."
)

if ranked_news:

    if st.button("Select Best Story and Extract Facts", type="primary"):

        with st.spinner(
            "Evaluating ranked stories and extracting facts..."
        ):

            for key in [
                "selected_news",
                "verified_data",
                "generated_article",
                "generated_carousel"
            ]:
                st.session_state.pop(key, None)

            # Only evaluate stories that passed editorial eligibility.
            eligible_candidates = [
                news for news in ranked_news
                if news.get("eligible_for_selection") is True
            ]

            # Evaluate eligible stories in ranking order.
            candidates = eligible_candidates[:10]

            evaluation_results = []

            for candidate in candidates:

                title = candidate.get("title", "Untitled")

                try:
                    result = verify_news(candidate)

                    valid, message = validate_news(result)

                    evaluation_results.append({
                        "title": title,
                        "score": candidate.get("score", 0),
                        "status": "Passed" if valid else "Failed",
                        "reason": message
                    })

                    if valid:
                        st.session_state["selected_news"] = candidate
                        st.session_state["verified_data"] = result
                        break

                except Exception as error:

                    evaluation_results.append({
                        "title": title,
                        "score": candidate.get("score", 0),
                        "status": "Failed",
                        "reason": str(error)
                    })

            st.session_state["candidate_evaluations"] = evaluation_results

            if "selected_news" not in st.session_state:
                if not eligible_candidates:
                    st.error(
                        "No stories passed editorial eligibility. "
                        "Please collect and rank news again."
                    )
                else:
                    st.error(
                        "No eligible candidate passed original article "
                        "extraction and validation."
                    )


selected_news = st.session_state.get("selected_news")

verified_data = st.session_state.get("verified_data")


if selected_news and verified_data:

    st.success("The agent has selected a suitable news story.")

    st.subheader("🏆 Selected Winning Story")

    st.markdown(
        f"### {selected_news.get('title', 'Untitled')}"
    )

    col1, col2 = st.columns(2)

    col1.metric(
        "Winning score",
        selected_news.get("score", 0)
    )

    col2.metric(
        "Candidates evaluated",
        min(10, len(ranked_news))
    )

    st.write(
        "**Publisher:**",
        selected_news.get("source", "Unknown")
    )

    st.write(
        "**Published:**",
        selected_news.get("published", "Unknown")
    )

    if selected_news.get("link"):
        st.markdown(
            f"[Read selected article]({selected_news['link']})"
        )

    st.subheader("Why This Story Won")

    st.write(
        "This story had the highest ranking score among the "
        "candidates that also provided sufficient extractable facts."
    )

    for reason in selected_news.get("selection_reasons", []):
        st.write(f"- {reason}")

    st.write("**Winning score breakdown:**")
    st.write(selected_news.get("scores", {}))

    st.subheader("Comparison With Other Ranked Stories")

    for competitor in ranked_news[:10]:

        if competitor.get("link") == selected_news.get("link"):
            continue

        winner_score = float(selected_news.get("score", 0))
        competitor_score = float(competitor.get("score", 0))

        difference = winner_score - competitor_score

        with st.expander(
            f"{competitor.get('title', 'Untitled')} "
            f"— Score: {competitor.get('score', 0)}"
        ):

            st.write(
                f"**Score difference:** {difference:+.2f} points"
            )

            st.write("**Ranking reasons:**")

            for reason in competitor.get("selection_reasons", []):
                st.write(f"- {reason}")

    st.caption(
        "The comparison uses the ranking scores and scoring reasons. "
        "Candidates that could not provide sufficient article facts "
        "were skipped."
    )

    st.divider()

    # DISPLAY EXTRACTED FACTS

    st.subheader("Extracted Facts")

    st.write(
        "The following information was extracted from the selected "
        "news article."
    )

    st.info(
        verified_data.get("verification_status", "")
    )

    if verified_data.get("main_development"):
        st.write(
            "**Main development:**",
            verified_data["main_development"]
        )

    if verified_data.get("company"):
        st.write(
            "**Company:**",
            verified_data["company"]
        )

    if verified_data.get("location"):
        st.write(
            "**Location:**",
            verified_data["location"]
        )

    for index, fact in enumerate(
        get_verified_facts(verified_data), 1
    ):
        st.write(f"{index}. {fact}")

    if verified_data.get("important_figures"):

        st.subheader("Important Figures")

        for figure in verified_data["important_figures"]:

            st.write(
                f"**{figure.get('value', '')}** — "
                f"{figure.get('description', '')}"
            )

    if verified_data.get("missing_information"):

        st.warning(
            "Some information was not available in the selected article:"
        )

        for item in verified_data["missing_information"]:
            st.write(f"- {item}")

    st.subheader("Sources and References")

    for source in get_sources(verified_data):

        st.markdown(
            f"- [{source['name']}]({source['url']})"
        )

    st.caption(
        "Facts are extracted from the listed article. "
        "Independent verification against additional sources "
        "is recommended before publication."
    )

else:

    st.info(
        "Collect and rank news, then select the winning story "
        "to see its extracted facts."
    )


st.divider()


# SECTION 3: LINKEDIN ARTICLE GENERATION

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
                        use_ai=True
                    )

                    st.session_state["generated_article"] = article

                    # A new article requires a fresh carousel
                    st.session_state.pop(
                        "generated_carousel",
                        None
                    )

                except Exception as error:

                    st.error(
                        f"Article generation failed: {error}"
                    )


article = st.session_state.get("generated_article")


if article:

    st.subheader("Generated LinkedIn Article")

    st.markdown(article)

    st.subheader("Article References")

    for source in get_sources(verified_data):

        st.markdown(
            f"- [{source['name']}]({source['url']})"
        )

    st.info(
        "Review the article and check the facts before publishing."
    )

else:

    if not selected_news:
        st.info(
            "Select a winning story before generating the article."
        )


st.divider()


# SECTION 4: SIX-SLIDE LINKEDIN CAROUSEL

st.header("4. Generate Six-Slide LinkedIn Carousel")

st.write(
    "Create a six-slide LinkedIn carousel from the same selected "
    "news and extracted facts used for the article."
)

if article and selected_news and verified_data:

    st.write(
        "The carousel follows ChemStride's professional writing style "
        "and uses the same source information as the article."
    )

    if st.button("Generate 6-Slide LinkedIn Carousel", type="primary"):

        with st.spinner(
            "Creating six carousel slides and preparing PDF..."
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

                st.error(
                    f"Carousel generation failed: {error}"
                )


carousel = st.session_state.get("generated_carousel")


if carousel:

    st.subheader("Carousel Preview")
    st.success(f"Selected theme: {carousel.get('theme', 'Generated theme')}")

    slides = carousel.get("slides", [])
    pdf_bytes = carousel.get("pdf")

    if slides and pdf_bytes:

        st.caption(
            "Previewing the actual PDF page as an image. "
            "The downloaded PDF contains the same slide design."
        )

        if fitz is None:
            st.error(
                "Slide preview needs PyMuPDF. Install it with "
                "`pip install pymupdf`, add `pymupdf` to requirements.txt, "
                "and restart the app. You can still download the PDF below."
            )
        else:
            # Keep the selected slide in Streamlit session state.
            current_index = st.session_state.get("carousel_index", 0)
            current_index = max(0, min(current_index, len(slides) - 1))
            st.session_state["carousel_index"] = current_index

            previous_col, counter_col, next_col = st.columns([1, 1, 1])

            with previous_col:
                if st.button(
                    "← Previous",
                    key="carousel_previous",
                    disabled=current_index == 0,
                    use_container_width=True,
                ):
                    st.session_state["carousel_index"] = current_index - 1
                    st.rerun()

            with counter_col:
                st.markdown(
                    f"<div style='text-align:center; padding:8px 0; "
                    f"font-weight:800; color:#E21B23;'>"
                    f"SLIDE {current_index + 1:02d} / {len(slides):02d}</div>",
                    unsafe_allow_html=True,
                )

            with next_col:
                if st.button(
                    "Next →",
                    key="carousel_next",
                    disabled=current_index >= len(slides) - 1,
                    use_container_width=True,
                ):
                    st.session_state["carousel_index"] = current_index + 1
                    st.rerun()

            # Fullscreen-compatible keyboard navigation.
            components.html(
                """
                <script>
                (function () {
                    const parentWindow = window.parent;
                    const parentDocument = parentWindow.document;

                    // Attach once to the parent document so the handler remains
                    // active when Streamlit opens its image fullscreen viewer.
                    if (parentWindow.__chemstrideCarouselKeysAttached) return;
                    parentWindow.__chemstrideCarouselKeysAttached = true;

                    parentDocument.addEventListener("keydown", function (event) {
                        if (event.altKey || event.ctrlKey || event.metaKey) return;

                        const active = parentDocument.activeElement;
                        const tag = active ? active.tagName.toLowerCase() : "";
                        const typing = tag === "input" || tag === "textarea" ||
                            (active && active.isContentEditable);

                        if (typing) return;

                        let targetText = null;

                        if (event.key === "ArrowLeft") {
                            targetText = "← Previous";
                        }

                        if (event.key === "ArrowRight") {
                            targetText = "Next →";
                        }

                        if (!targetText) return;

                        const buttons = Array.from(
                            parentDocument.querySelectorAll("button")
                        );

                        const target = buttons.find(button =>
                            button.innerText.trim() === targetText
                        );

                        if (target && !target.disabled) {
                            event.preventDefault();
                            event.stopPropagation();

                            if (
                                typeof event.stopImmediatePropagation === "function"
                            ) {
                                event.stopImmediatePropagation();
                            }

                            target.click();
                        }
                    }, true);
                })();
                </script>
                """,
                height=0,
                scrolling=False,
            )

            try:
                # Render the actual PDF page as a centered, readable preview.
                with fitz.open(
                    stream=pdf_bytes,
                    filetype="pdf"
                ) as pdf_document:

                    if len(pdf_document) != len(slides):
                        st.warning(
                            f"The PDF contains {len(pdf_document)} pages, "
                            f"while the slide data contains {len(slides)} slides."
                        )

                    page_index = min(
                        current_index,
                        len(pdf_document) - 1
                    )

                    page = pdf_document.load_page(page_index)

                    pixmap = page.get_pixmap(
                        matrix=fitz.Matrix(1.5, 1.5),
                        alpha=False,
                    )

                    slide_png = pixmap.tobytes("png")

                left_space, preview_col, right_space = st.columns([1, 2, 1])

                with preview_col:
                    st.image(
                        slide_png,
                        width=720,
                        caption=f"Slide {current_index + 1} of {len(slides)}",
                    )

            except Exception as error:
                st.error(f"Could not render the slide preview: {error}")
                st.caption("The PDF download is still available below.")

        st.divider()

        st.download_button(
            label="Download LinkedIn Carousel (PDF)",
            data=pdf_bytes,
            file_name=carousel.get(
                "filename",
                "chemstride_linkedin_carousel.pdf",
            ),
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )

        st.subheader("Carousel References")

        for source in get_sources(verified_data):
            source_name = source.get("name", "Original source")
            source_url = source.get("url", "")

            if source_url:
                st.markdown(f"- [{source_name}]({source_url})")
            else:
                st.write(f"- {source_name}")

        st.info(
            "The carousel uses the extracted facts from the selected article. "
            "Review all six slides and references before publishing."
        )

    else:
        st.error("The generated carousel or PDF is missing.")

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


st.divider()

st.caption(
    "ChemStride Chemical Industry News Agent | "
    "AI-Assisted News Research and LinkedIn Content Generation"
)