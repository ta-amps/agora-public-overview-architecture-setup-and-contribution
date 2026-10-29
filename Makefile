.PHONY: check

check:
	python3 -m unittest discover -s tests -v
	python3 scripts/check.py
	python3 scripts/build_site.py --check
