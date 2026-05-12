# Madusa Analytics Seed — operator commands.

.PHONY: install test connect reset reset-apply verify accept-phase3-reset accept-phase3-verify

install:
	pip install -e ".[dev]"

test:
	pytest -v

connect:
	python -m tools.connect_madusa

reset:
	python -m tools.reset_madusa_kb

reset-apply:
	python -m tools.reset_madusa_kb --apply

verify:
	@if [ -z "$(RUN_ID)" ]; then echo "RUN_ID is required: make verify RUN_ID=<id>"; exit 2; fi
	python -m tools.verify_hydration --run-id $(RUN_ID) $(if $(LOG_FILE),--log-file $(LOG_FILE),)

# Step 1 of acceptance: soft-wipe Madusa KB so Generate KB has a clean slate.
# Step 2 (manual): operator triggers a Generate KB run in the UI and grabs the RUN_ID.
# Step 3 of acceptance: run verify against the RUN_ID.
accept-phase3-reset:
	$(MAKE) reset-apply

accept-phase3-verify:
	@if [ -z "$(RUN_ID)" ]; then echo "RUN_ID is required: make accept-phase3-verify RUN_ID=<id>"; exit 2; fi
	$(MAKE) verify RUN_ID=$(RUN_ID) $(if $(LOG_FILE),LOG_FILE=$(LOG_FILE),)
