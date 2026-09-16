"""Ranks retrieved abstracts by evidence tier (systematic review/RCT first) and recency."""


def rank_abstracts(abstracts):
    high_tier = {"Systematic Review", "Randomized Controlled Trial"}

    def is_high_tier(abstract):
        return any(pt in high_tier for pt in abstract["publication_type"])

    return sorted(
        abstracts,
        key=lambda a: (not is_high_tier(a), -int(a["publication_date"])),
    )
