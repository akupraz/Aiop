import os
import json
import re
import requests
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

api_key = os.getenv('ANTHROPIC_API_KEY')

SYSTEM_PROMPT = """Kamu adalah analis teknikal profesional untuk saham IDX. 

Analisis chart dengan fokus:
1. Support levels (3-5 level)
2. Resistance levels (3-5 level)
3. Trading plan: entry, stop loss, targets, risk/reward
4. Rekomendasi: SHORT/LONG/AVOID
5. Confidence level (0-100%)

Output: JSON ONLY"""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    if not api_key:
        return jsonify({"status": "error", "message": "API key not set"}), 500
    
    try:
        data = request.json
        saham_code = data.get('saham_code', '').upper()
        chart_description = data.get('chart_description', '')
        current_price = data.get('current_price', '')
        timeframe = data.get('timeframe', 'daily')
        bandarmologi_data = data.get('bandarmologi_data', '')
        
        user_message = f"""Analisa chart untuk saham: {saham_code}
Data: Harga Rp {current_price}, Timeframe {timeframe}
Deskripsi: {chart_description}
Bandarmologi: {bandarmologi_data}
Output JSON format."""
        
        headers = {
            "x-api-key": api_key,
            "content-type": "application/json"
        }
        
        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 1000,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": user_message}]
        }
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code != 200:
            return jsonify({
                "status": "error",
                "message": f"API Error: {response.status_code}"
            }), 400
        
        response_data = response.json()
        result_text = response_data.get('content', [{}])[0].get('text', '')
        
        try:
            result_json = json.loads(result_text)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_json = json.loads(json_match.group())
            else:
                result_json = {"raw_response": result_text}
        
        input_tokens = response_data.get('usage', {}).get('input_tokens', 0)
        output_tokens = response_data.get('usage', {}).get('output_tokens', 0)
        cost = (input_tokens / 1_000_000 * 3.00) + (output_tokens / 1_000_000 * 15.00)
        
        return jsonify({
            "status": "success",
            "data": result_json,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": f"{cost:.4f}"
            }
        })
    
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
