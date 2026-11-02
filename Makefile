.PHONY: check light-check share-card

check:
	python3 -m unittest discover -s tests -v
	python3 scripts/check.py
	python3 scripts/build_site.py --check

# MUST-FOLLOW rule 13: every current page in Chromium under the light and the dark colour scheme (needs Playwright).
light-check:
	python3 scripts/light_check.py

# The og:image, drawn light from site.json's share card (needs Playwright).
share-card:
	python3 scripts/share_card.py
