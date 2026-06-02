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

client = Anthropic()

SYSTEM_PROMPT = """Kamu adalah analis teknikal profesional untuk saham IDX. 

Analisis chart dengan fokus:
1. Support levels (3-5 level dari terendah ke tertinggi)
2. Resistance levels (3-5 level)
3. Trading plan:
   - Entry point & logic
   - Target prices (TP1, TP2, TP3)
   - Stop loss
   - Risk/reward ratio
   - Holding time estimate
4. Rekomendasi: SCALPING / FAST TRADING / SWING / AVOID
5. Confidence level (0-100%)

Pertimbangkan:
- Trend direction (uptrend/downtrend/sideways)
- Moving averages alignment
- Volume pattern (accumulation/distribution)
- Bandarmologi signals (foreign flow, broker activity)
- Wyckoff phases jika applicable

PENTING: Output HANYA JSON format (no explanation text)
"""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        
        saham_code = data.get('saham_code', '').upper()
        chart_description = data.get('chart_description', '')
        current_price = data.get('current_price', '')
        timeframe = data.get('timeframe', 'daily')
        bandarmologi_data = data.get('bandarmologi_data', '')
        
        user_message = f"""
Analisa chart untuk saham: {saham_code}

Data:
- Harga saat ini: Rp {current_price}
- Timeframe: {timeframe}
- Deskripsi chart: {chart_description}

Bandarmologi data:
{bandarmologi_data}

Berikan analisis lengkap: support, resistance, trading plan, confidence.
Format: JSON ONLY dengan struktur:
{
  "code": "SAHAM",
  "current_price": number,
  "support_levels": [{"level": number, "strength": "STRONG/MEDIUM/WEAK", "note": "..."}],
  "resistance_levels": [{"level": number, "strength": "STRONG/MEDIUM/WEAK", "note": "..."}],
  "trading_plan": {
    "recommendation": "SHORT/LONG/AVOID",
    "type": "SCALPING/FAST_TRADING/SWING",
    "entry": "...",
    "stop_loss": number,
    "targets": [number, number],
    "risk_reward": "...",
    "holding_time": "..."
  },
  "bandarmologi": {
    "foreign_flow": "BUYING/SELLING/NEUTRAL",
    "dominant_broker": "...",
    "imbalance": "...",
    "interpretation": "..."
  },
  "confidence": number,
  "key_watch": "..."
}
"""
        
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_message}
            ]
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
        
        print(f"\n✅ Analisis {saham_code} selesai")
        print(f"Input tokens: {response.usage.input_tokens}")
        print(f"Output tokens: {response.usage.output_tokens}")
        cost = (response.usage.input_tokens / 1_000_000 * 3.00) + (response.usage.output_tokens / 1_000_000 * 15.00)
        print(f"Cost: ${cost:.4f}")
        
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
    print("🚀 Starting AIOP RDFE Analyzer...")
    print("Akses di: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
