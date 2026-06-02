import os
import json
import re
from flask import Flask, render_template, request, jsonify
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Anthropic client safely
try:
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    client = Anthropic(api_key=api_key)
except Exception as e:
    print(f"Error initializing Anthropic client: {e}")
    client = None

SYSTEM_PROMPT = """Kamu adalah analis teknikal profesional untuk saham IDX. 

Analisis chart dengan fokus:
1. Support levels (3-5 level dari terendah ke tertinggi)
2. Resistance levels (3-5 level)
3. Trading plan dengan entry, stop loss, targets, risk/reward
4. Rekomendasi: SHORT/LONG/AVOID
5. Confidence level (0-100%)

Output: JSON ONLY (no explanation)
"""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    if not client:
        return jsonify({
            "status": "error",
            "message": "Anthropic client not initialized. Check API key."
        }), 500
    
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
        
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}]
        )
        
        result_text = response.content[0].text
        
        try:
            result_json = json.loads(result_text)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_json = json.loads(json_match.group())
            else:
                result_json = {"raw_response": result_text}
        
        cost = (response.usage.input_tokens / 1_000_000 * 3.00) + (response.usage.output_tokens / 1_000_000 * 15.00)
        print(f"✅ {saham_code}: {response.usage.input_tokens} tokens, ${cost:.4f}")
        
        return jsonify({
            "status": "success",
            "data": result_json,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cost_usd": f"{cost:.4f}"
            }
        })
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
