
VERIFIED_NEWS = {
    "title": "Kutch Chemical commissions a major chlor-alkali plant",
    "company": "Kutch Chemical Industries Limited",

    "facts": [
        "The plant is located in Padana, Gujarat, India.",
        "The plant has an annual caustic soda production capacity of 220,000 metric tonnes.",
        "The plant was commissioned on 5 November 2026.",
        "The facility uses five electrolyzers based on BM Generation 6+ technology.",
        "Kutch Chemical plans to use the caustic soda and chlorine for its own production and sales in the Indian market."
    ],

    "sources": [
        {
            "name": "thyssenkrupp nucera",
            "url": "https://investors.thyssenkrupp-nucera.com/news/thyssenkrupp-nucera-commissions-major-chlor-alkali-plant-for-kutch-chemical-in-india/54e1b42e-afc0-4f19-88ee-be3190285e47"
        },
        {
            "name": "Chemical Engineering",
            "url": "https://www.chemengonline.com/thyssenkrupp-nucera-commissions-chlor-alkali-plant-for-kutch-chemical-in-india/"
        }
    ]
}


def get_verified_facts():
    return VERIFIED_NEWS["facts"]


def get_sources():
    return VERIFIED_NEWS["sources"]


def validate_news():
    facts = get_verified_facts()
    sources = get_sources()

    if not facts:
        return False, "No verified facts available."

    if not sources:
        return False, "No source links available."

    return True, "Source verification record is ready."


if __name__ == "__main__":
    valid, message = validate_news()

    print("\nSOURCE VERIFICATION")
    print(message)

    print("\nVERIFIED FACTS:")
    for index, fact in enumerate(get_verified_facts(), 1):
        print(f"{index}. {fact}")

    print("\nSOURCES:")
    for source in get_sources():
        print(f"{source['name']}: {source['url']}")
