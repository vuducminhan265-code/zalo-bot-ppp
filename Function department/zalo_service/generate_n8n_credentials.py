import os
import sys
import json
import base64

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

DEFAULT_KEY = base64.b64decode("QVEuQWI4Uk42SkZGZ2ZDdDJ6OVc4WV8yVEZUckV6ck9SY284Y1FoTjRLTmc5MjV3ZmdwSkE=").decode()
api_key = os.getenv("GEMINI_API_KEY", DEFAULT_KEY)

creds = [
    {
        "id": "1",
        "name": "Google Gemini(PaLM) Api account",
        "type": "googlePalmApi",
        "data": {
            "apiKey": api_key
        }
    }
]

out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "n8n_credentials.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(creds, f, ensure_ascii=False, indent=2)

print(f"✅ Generated n8n credentials at {out_path}")
