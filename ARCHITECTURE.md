# System Architecture – ChemStride Chemical Industry News Agent

## 1. Architecture Overview

The application follows a modular Python architecture. Each module handles a specific responsibility, making the application easier to understand, maintain and extend.

Streamlit acts as the user interface and connects the news collection, filtering, ranking, source verification and article generation modules.

The system combines automated news discovery and ranking with manually reviewed industry information to generate business-oriented LinkedIn articles.

## 2. System Architecture Diagram

```text
                       USER
                         |
                         v
                STREAMLIT DASHBOARD
                      app.py
                         |
             +-----------+-----------+
             |           |           |
             v           v           v
        NEWS DISCOVERY  SELECTED    ARTICLE
                       DEVELOPMENT GENERATION
             |           |           |
             v           v           v
       NEWS COLLECTOR  SOURCE     STYLE GUIDE
             |        VERIFIER        |
             v           |            v
       GOOGLE NEWS       v         PROMPT
          RSS         VERIFIED    CREATION
             |          FACTS         |
             v                        v
       NEWS FILTERING              GEMINI API
             |                        |
             v                        v
        NEWS RANKER               ARTICLE DRAFT
             |
             v
       RANKED NEWS RESULTS
             |
             v
       STREAMLIT DASHBOARD
```

## 3. Module Responsibilities

### A. app.py – Application Interface

- Provides the Streamlit dashboard.
- Triggers news collection and processing.
- Displays article counts and ranking results.
- Shows the highest-ranked news articles with their scores and selection reasons.
- Presents the selected industry development and supporting references.
- Triggers LinkedIn article generation.
- Displays the generated article and its references.

### B. news_collector.py – News Collection

- Collects news from Google News RSS feeds.
- Searches across multiple chemical industry topics.
- Extracts headlines, publication dates, summaries, links and publishers.
- Removes duplicate news entries based on article links.

### C. news_filter.py – News Filtering

- Checks article publication dates.
- Keeps news published within the configured recent-news period.
- Identifies relevant chemical industry keywords.
- Removes articles that do not match the filtering criteria.

### D. news_ranker.py – News Ranking

Ranks filtered news using a custom rule-based scoring algorithm. Each article receives points based on its industry relevance, importance of the development, potential business impact and recency.

| Criterion | Maximum Points |
|---|---:|
| Business Relevance | 30 |
| Industry Development | 35 |
| Business / Supply Chain Impact | 20 |
| Recency | 15 |
| **Base Score** | **100** |

The ranking system also:

- Adds a specificity bonus of up to 5 points.
- Applies penalties to less relevant content, such as generic reports, stock-related news and awards.
- Provides selection reasons to explain why an article received its ranking.
- Uses headline similarity to identify and remove near-duplicate articles.

The final ranking is based on predefined keywords and scoring rules rather than a machine-learning model.

### E. source_verifier.py – Source Verification

- Maintains the selected news development.
- Stores manually reviewed factual information.
- Maintains supporting source names and links.
- Provides verified facts and references required for article generation.

### F. style_guide.py – Writing Style

Defines the ChemStride LinkedIn writing guidelines, including:

- Professional and approachable tone.
- Simple and natural English.
- Short paragraphs and clear headings.
- Business-oriented explanations.
- Relevant industry takeaways.
- Appropriate calls to action and hashtags.

### G. article_generator.py – AI Article Generation

- Creates the article-generation prompt.
- Combines selected news details, verified facts and writing guidelines.
- Sends the prompt to the Gemini API.
- Receives and returns the generated article.
- Provides a basic fallback draft if AI generation fails.

## 4. End-to-End Workflow

**Step 1: News Discovery**

The application searches multiple chemical industry topics through Google News RSS.

**Step 2: News Filtering**

Collected articles are checked for recency and relevance using predefined keywords.

**Step 3: Ranking**

Relevant articles are scored using the custom ranking algorithm. The system considers business relevance, industry development, business impact and recency, with additional bonuses and penalties where applicable.

**Step 4: Editorial Selection**

The application displays the highest-ranked news articles with their scores and selection reasons. A selected chemical industry development is maintained separately for detailed analysis.

**Step 5: Source Verification**

The source verification module provides manually reviewed facts and supporting references for the selected Kutch Chemical development.

**Step 6: Article Generation**

The article generator combines the selected development, verified facts and ChemStride writing guidelines to create a prompt for the Gemini API.

**Step 7: Output Display**

The generated LinkedIn article, selected news information and supporting source references are displayed in the Streamlit dashboard.

## 5. Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| User Interface | Streamlit |
| News Discovery | Google News RSS |
| RSS Processing | Feedparser |
| News Filtering | Python keyword-based rules |
| Ranking | Custom Python scoring algorithm |
| Duplicate Detection | SequenceMatcher and link-based checks |
| AI Article Generation | Google Gemini API |
| Environment Configuration | python-dotenv |

## 6. Error Handling

The application includes basic error handling for:

- News collection failures.
- Missing verified facts.
- Gemini API errors.
- Empty AI responses.
- API availability and timeout issues.

The article generator also includes retry handling for temporary API failures.

When Gemini is unavailable, the article generator returns a basic fallback draft using the supplied facts.

## 7. Current Limitations

- News ranking is based on predefined rules and keywords.
- News relevance is evaluated primarily from headlines and RSS summaries.
- Duplicate detection is based on links and headline similarity.
- Source verification is manually configured for the selected development.
- Gemini generation depends on external API availability.
- Human review is required before publishing an article.

## 8. Future Scope

The system can be extended with:

- Semantic news ranking.
- Automated source verification.
- Additional industry-specific news sources.
- Historical news storage.
- Improved article-generation reliability.
- User-controlled news selection and article generation.

## 9. Conclusion

The modular architecture separates news discovery, processing, ranking, verification and content generation.

This structure makes it possible to improve individual components without redesigning the entire application. By combining automated news processing with manually reviewed information and AI-assisted writing, the system provides a structured approach to identifying relevant chemical industry developments and preparing business-oriented content.