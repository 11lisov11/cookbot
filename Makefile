.PHONY: check backend fake-mega web firmware

check:
	bash scripts/check_all.sh

backend:
	python -m uvicorn unoq_backend.app:app --host 127.0.0.1 --port 8000

fake-mega:
	python -m unoq_backend.fake_mega

web:
	cd web && npm run dev

firmware:
	arduino-cli compile --fqbn arduino:avr:mega mega_firmware/cookbot_mega_firmware

