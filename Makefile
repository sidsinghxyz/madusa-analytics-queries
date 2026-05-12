# Madusa Analytics Seed — operator commands.

.PHONY: install test connect reset reset-apply verify accept-phase3

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

# Chain reset → (user triggers Generate KB run via UI or curl) → verify
# RUN_ID is provided after the trigger.
accept-phase3:
	@if [ -z "$(RUN_ID)" ]; then echo "RUN_ID is required: make accept-phase3 RUN_ID=<id>"; exit 2; fi
	$(MAKE) reset-apply
	$(MAKE) verify RUN_ID=$(RUN_ID)
