# config.py

BASE_IP = "4.194.122.32"  # <-- change only this if IP changes (VM IP Address)
BASE_URL = f"http://{BASE_IP}:8000" #

RATE_PER_HOUR = 0.65  # <-- change if diff rate (make sure change also for frontend)

terminal = 1 #for dummy payment only needed

refresh_token = "c5a91474e7c4f557b24e4e5b31f22c13ff003729f3c8ff814d47589f196a5257" #refresh token for pegepay