# ChemStride – Chemical Industry News Agent

## Project Overview

The **ChemStride Chemical Industry News Agent** is a Python-based application designed to discover, filter and rank recent chemical industry news and generate LinkedIn article drafts.

The application collects news from multiple chemical industry topics, identifies relevant developments, assigns editorial ranking scores and presents the results through an interactive Streamlit dashboard.

It also includes a selected industry development with manually curated supporting facts and source references, along with AI-assisted article generation using Google's Gemini API.

## Key Features

- **News Collection:** Collects chemical industry news from multiple Google News RSS searches.
- **News Filtering:** Filters articles based on publication dates and relevant industry keywords.
- **Duplicate Removal:** Removes duplicate links and similar headlines.
- **News Ranking:** Scores articles using business relevance, industry developments, business impact and recency.
- **Selection Explanations:** Displays reasons behind article rankings based on matched keywords and editorial scoring rules.
- **Editorial Selection:** Presents a selected chemical industry development for further analysis.
- **Source Verification:** Maintains a manually curated record of facts and supporting source links for the selected development.
- **AI Article Generation:** Uses Google's Gemini API to generate LinkedIn article drafts from supplied facts.
- **Writing Style Guidance:** Applies a predefined ChemStride writing guide to maintain a professional and approachable tone.
- **Fallback Generation:** Provides a basic article draft if Gemini generation is unavailable.
- **Interactive Dashboard:** Displays news results, ranking scores, selected developments, generated articles and source references through Streamlit.

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| Streamlit | Interactive dashboard |
| Feedparser | Reading RSS feeds |
| Google News RSS | News discovery |
| Google Gemini API | AI-assisted article generation |
| Google Gen AI SDK | Gemini API integration |
| python-dotenv | Environment variable management |
| difflib | Similar headline detection |

## Project Structure

```text
chemical-news-agent/
│
├── app.py
├── requirements.txt
├── .gitignore
├── .env.example
├── README.md
│
└── modules/
    ├── __init__.py
    ├── news_collector.py
    ├── news_filter.py
    ├── news_ranker.py
    ├── source_verifier.py
    ├── article_generator.py
    └── style_guide.py
```

The `.env` file and virtual environment are kept locally and should not be uploaded to GitHub.

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/vanshita-vilas-parab/chemical-news-agent.git
cd chemical-news-agent
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
```

### 3. Activate the environment

For macOS and Linux:

```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

Create a `.env` file in the project root directory.

Add your Gemini API configuration:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=your_available_gemini_model
```

Obtain an API key through [Google AI Studio](https://aistudio.google.com/).

Keep your API key private. Never upload your `.env` file to GitHub.

### 6. Run the application

```bash
streamlit run app.py
```

The application will generally be available at:

```text
http://localhost:8501
```

## How the Application Works

1. **News Collection:** Collects chemical industry news from multiple Google News RSS searches.
2. **News Filtering:** Filters collected articles based on publication dates and relevant industry keywords.
3. **Duplicate Removal:** Removes duplicate links and similar headlines.
4. **News Ranking:** Calculates scores for the remaining articles using predefined editorial rules.
5. **Editorial Selection:** Presents a selected industry development with its supporting facts and source references.
6. **Prompt Preparation:** Combines the selected news information, supplied facts and ChemStride writing guidelines.
7. **AI Article Generation:** Sends the prepared prompt to Google's Gemini API to generate a LinkedIn article draft.
8. **Output Display:** Displays the generated article and its supporting references in the Streamlit dashboard.

## News Ranking Methodology

The application uses a predefined keyword-based scoring system to prioritize relevant chemical industry developments.

| Ranking Criterion | Maximum Score |
|---|---:|
| Business Relevance | 30 |
| Industry Development | 35 |
| Business and Supply-Chain Impact | 20 |
| Recency | 15 |
| **Total Before Penalties** | **100** |

Additional editorial penalties are applied to lower-priority content, including:
- Negative incidents and industrial accidents.
- Stock-focused articles.
- Generic market forecasts and research reports.

The final score is capped between 0 and 100.

The ranking system uses predefined keywords and rules. It is an editorial scoring approach, not a trained machine learning model or a semantic understanding system.

## Selected Industry Development

**Kutch Chemical commissions a major chlor-alkali plant in Gujarat.**

The selected development concerns Kutch Chemical Industries Limited and its facility in Padana, Gujarat.

The manually maintained verification record includes:

- Annual caustic soda production capacity of 220,000 metric tonnes.
- Commissioning date of 5 November 2026.
- Five electrolyzers based on BM Generation 6+ technology.
- Planned use of caustic soda and chlorine for internal production and sales in the Indian market.

### Supporting References

- [thyssenkrupp nucera – Official announcement](https://investors.thyssenkrupp-nucera.com/news/thyssenkrupp-nucera-commissions-major-chlor-alkali-plant-for-kutch-chemical-in-india/54e1b42e-afc0-4f19-88ee-be3190285e47)
- [Chemical Engineering – Related coverage](https://www.chemengonline.com/thyssenkrupp-nucera-commissions-chlor-alkali-plant-for-kutch-chemical-in-india/)

The facts for this selected development are maintained in a manually curated verification record. The application does not automatically fact-check every collected news article.

## AI-Assisted Article Generation

The article generator uses Google's Gemini API to prepare LinkedIn article drafts.

The prompt combines:

- Selected news headline and publication information.
- Supplied verified facts.
- ChemStride writing style guidelines.
- Instructions for article structure and business relevance.
- Restrictions against unsupported statistics, quotations and claims.

If Gemini generation fails or is unavailable, the application provides a basic fallback draft using the supplied information.

Generated articles should be reviewed before publication.

## Limitations

- News discovery depends on RSS feed availability and the quality of the returned articles.
- The ranking system uses keyword-based scoring and may not fully understand the context of every article.
- Similarity-based duplicate removal may not identify every version of the same story.
- Source verification is manually maintained for the selected development rather than automatically performed for all collected news.
- AI article generation depends on Gemini API availability, network connectivity and usage limits.
- Generated articles require human review before publication.
- The application prepares article drafts but does not automatically publish content to LinkedIn.

## Future Improvements

- Improve news ranking through semantic similarity and contextual analysis.
- Automate source discovery and fact verification.
- Integrate additional chemical industry news sources.
- Improve article generation reliability and response handling.
- Maintain historical news records and article-generation history.
- Add user-controlled topic selection.

## Conclusion

The ChemStride Chemical Industry News Agent brings together chemical industry news discovery, filtering, ranking, editorial selection, source references and AI-assisted content generation in one application.

It aims to reduce the effort involved in identifying relevant industry developments and preparing informative LinkedIn article drafts while keeping human review and editorial judgment part of the process.

---

**Repository:** [ChemStride – Chemical Industry News Agent](https://github.com/vanshita-vilas-parab/chemical-news-agent)
