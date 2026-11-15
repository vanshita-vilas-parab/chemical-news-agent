---
runme:
  document:
    relativePath: README.md
  session:
    id: 01M7E7FKJVYP17S40JBA4VBC4R
    updated: 2026-11-15 05:21:46+05:30
---

# ChemStride – Chemical Industry News Agent

## Project Overview

The ChemStride Chemical Industry News Agent is a Python-based application designed to discover, filter and rank recent chemical industry news and generate LinkedIn article drafts.

The application gathers news from multiple chemical industry topics, identifies relevant developments, assigns ranking scores and presents the results through an interactive Streamlit dashboard.

It also includes a selected industry development, supporting source references and AI-assisted article generation using Google's Gemini API.

## Key Features

- **News Collection:** Collects news from multiple chemical industry topics using Google News RSS feeds.
- **News Filtering:** Filters articles based on publication date and relevant chemical industry keywords.
- **Duplicate Removal:** Removes duplicate links and similar headlines.
- **News Ranking:** Ranks news using relevance, industry impact, recency and business opportunity scores.
- **Topic Selection:** Presents a selected chemical industry development for further analysis.
- **Source Verification:** Maintains a record of verified facts and supporting source links for the selected development.
- **AI Article Generation:** Uses the Gemini API to generate LinkedIn article drafts based on verified information.
- **Writing Style Guidance:** Applies a predefined ChemStride writing guide to maintain a professional and approachable tone.
- **Interactive Dashboard:** Displays collected news, ranking results, selected development, generated article and references through Streamlit.

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| Streamlit | Interactive web application |
| Feedparser | Reading RSS news feeds |
| Google News RSS | News discovery |
| Google Gemini API | AI-assisted article generation |
| python-dotenv | Environment variable management |
| Requests | HTTP support |
| Pandas | Data handling dependency |

## Project Structure

```text
chemical-news-agent/
│
├── app.py
├── requirements.txt
├── .env
├── .env.example
├── README.md
├── ARCHITECTURE.md
│
├── modules/
│   ├── __init__.py
│   ├── news_collector.py
│   ├── news_filter.py
│   ├── news_ranker.py
│   ├── source_verifier.py
│   ├── article_generator.py
│   └── style_guide.py
│
└── data/
    └── news.json
```

## Installation and Setup

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
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

Add:

```env
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=your_available_gemini_model
```

Obtain a Gemini API key through Google AI Studio.

Keep your API key private. Do not upload your `.env` file to GitHub.

### 6. Run the application

```bash
streamlit run app.py
```

The application will open in your browser, usually at:

```text
http://localhost:8501
```

## How the Application Works

1. The application collects chemical industry news from multiple Google News RSS searches.
2. Collected articles are filtered based on their publication date and relevant keywords.
3. Duplicate and similar headlines are removed.
4. Remaining articles are assigned scores and ranked.
5. A selected industry development is presented with its supporting facts and references.
6. The article generator prepares a prompt using the verified facts and ChemStride writing style.
7. Gemini generates a LinkedIn article draft.
8. The generated article and source references are displayed in the dashboard.

## News Ranking Criteria

The ranking system uses four criteria:

| Criterion | Maximum Score |
|---|---:|
| Industry Relevance | 35 |
| Business and Industry Impact | 30 |
| Recency | 20 |
| Business Opportunity | 15 |
| **Total** | **100** |

The scores are calculated using predefined keyword-based rules.

## Selected Industry Development

**Kutch Chemical commissions a major chlor-alkali plant in Gujarat.**

The selected development includes an annual caustic soda production capacity of 220,000 metric tonnes at its facility in Padana, Gujarat.

The project information is supported by the following references:

- thyssenkrupp nucera
- Chemical Engineering

## Limitations

- News discovery depends on the availability and quality of RSS feeds.
- The ranking system uses predefined keywords and scoring rules rather than a trained machine learning model.
- Similarity-based duplicate removal may not identify every version of the same story.
- Source verification for the selected development is maintained through a manually curated record; it is not an automated fact-checking system for every collected article.
- AI article generation depends on Gemini API availability, network connectivity and usage limits.
- Generated articles require human review before publication.
- The application does not automatically publish content to LinkedIn.

## Future Improvements

- Improve news ranking using semantic similarity and contextual analysis.
- Automate source discovery and fact verification.
- Add more chemical industry news sources.
- Improve article generation reliability and response handling.
- Maintain historical news records and article-generation history.
- Add user-controlled topic selection.

## Conclusion

The ChemStride Chemical Industry News Agent brings together news discovery, filtering, ranking, source references and AI-assisted content generation in one application.

It aims to reduce the effort involved in identifying relevant chemical industry developments and preparing informative LinkedIn article drafts.