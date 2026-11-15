
CHEMSTRIDE_STYLE_GUIDE = {
    "tone": [
        "Professional and approachable",
        "Business-oriented and confident",
        "Friendly and natural",
        "Informative, not overly promotional"
    ],

    "language": [
        "Use simple, natural English",
        "Avoid complicated technical language where possible",
        "Keep paragraphs short and readable",
        "Avoid robotic or generic AI-sounding expressions"
    ],

    "headline": [
        "Start with an engaging headline",
        "Make the main development clear",
        "Create interest without exaggerating"
    ],

    "article_structure": [
        "Start with the main industry development",
        "Explain what happened using verified facts",
        "Use meaningful section headings",
        "Explain the business and industry implications",
        "End with a meaningful industry takeaway"
    ],

    "business_focus": [
        "Chemical manufacturing",
        "Supply chains and sourcing",
        "Domestic and international trade",
        "Industry growth and investment",
        "Business opportunities"
    ],

    "writing_style": [
        "Use short, well-spaced paragraphs",
        "Use questions as headings only when relevant",
        "Use bullet points when they improve readability",
        "Use emojis sparingly, if appropriate",
        "Include relevant hashtags",
        "Use a meaningful call to action when appropriate"
    ],

    "avoid": [
        "Inventing facts, figures or sources",
        "Unverified claims and exaggerated statements",
        "Unnecessary technical jargon",
        "Repetitive conclusions",
        "Overusing emojis and hashtags",
        "Making every article sound like an advertisement"
    ]
}


def get_style_guide():
    """Convert the style guide into instructions for the article generator."""

    prompt = "Follow this ChemStride LinkedIn writing style:\n"

    for section, instructions in CHEMSTRIDE_STYLE_GUIDE.items():
        prompt += f"\n{section.replace('_', ' ').title()}:\n"

        for instruction in instructions:
            prompt += f"- {instruction}\n"

    return prompt


if __name__ == "__main__":
    print(get_style_guide())
