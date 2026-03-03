import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Constants (In production, these come from .env.portal or secret vault)
WP_CLIENT_ID = os.getenv("WP_CLIENT_ID")
WP_CLIENT_SECRET = os.getenv("WP_CLIENT_SECRET")
REDIRECT_URI = os.getenv("PORTAL_REDIRECT_URI", "http://localhost:5000/callback")

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return jsonify({"error": "No code provided"}), 400

    # Exchange code for token
    token_url = "https://public-api.wordpress.com/oauth2/token"
    payload = {
        "client_id": WP_CLIENT_ID,
        "client_secret": WP_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }
    
    response = requests.post(token_url, data=payload)
    
    if response.status_code == 200:
        token_data = response.json()
        # Log to audit sink (future task)
        print(f"Token obtained for user: {token_data.get('blog_url')}")
        return jsonify({
            "status": "success",
            "message": "APΩ-Portal Identity Linked",
            "site": token_data.get('blog_url'),
            "access_token": token_data.get('access_token')[:10] + "..." # Masked
        })
    else:
        return jsonify({
            "status": "error",
            "details": response.json()
        }), response.status_code

@app.route('/login')
def login():
    auth_url = (
        f"https://public-api.wordpress.com/oauth2/authorize?"
        f"client_id={WP_CLIENT_ID}&"
        f"redirect_uri={REDIRECT_URI}&"
        f"response_type=code&"
        f"scope=auth sites posts"
    )
    return f'<a href="{auth_url}">Connect to APΩ-Portal via WordPress.com</a>'

if __name__ == '__main__':
    # Load env from .env.portal if exists
    if os.path.exists(".env.portal"):
        from dotenv import load_dotenv
        load_dotenv(".env.portal")
    
    app.run(port=5000, debug=True)
