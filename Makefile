.PHONY: setup doctor check test ledger gate master
setup:   ## install pinned typst into bin/ and sync python env
	./scripts/setup.sh
doctor:  ## check system prerequisites
	./scripts/doctor.sh
ledger:  ## schema, ids, uses, number traces (the owner's ledger and the example)
	uv run --frozen rc ledger check
	uv run --frozen rc ledger check ledger/example.yaml
test:
	uv run --frozen pytest -q
gate:    ## fit + ats + truth on every application whose meta.yaml status is ready
	uv run --frozen rc gate
master:  ## render master/selection.yaml (full-length reference; no fit constraints) to master/resume.pdf
	@if [ ! -f master/selection.yaml ]; then \
	  echo "master: no master/selection.yaml yet (onboarding creates it); nothing to render."; \
	else \
	  uv run --frozen rc truth master && \
	  uv run --frozen python -c "from pathlib import Path; import yaml; from rc import ledger, resolve, render; \
	    src = Path('build/master/resolved.yaml'); src.parent.mkdir(parents=True, exist_ok=True); \
	    src.write_text(yaml.safe_dump(resolve.resolve(yaml.safe_load(Path('master/selection.yaml').read_text()), ledger.load()), sort_keys=False, allow_unicode=True, width=1000)); \
	    print(render.render(src, Path('master/resume.pdf')))"; \
	fi
check: ledger test gate  ## THE gate. CI runs exactly this. Grows as phases land (see docs/spec.md §6).
