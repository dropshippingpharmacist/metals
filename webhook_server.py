from flask import Flask, request, jsonify
import json
import logging
import threading
from main import TCTMagicAnalyzer, Candle
from datetime import datetime
import os  # Add this with other imports

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
analyzer = TCTMagicAnalyzer()  # Initialize your bot

# Symbol mapping (TradingView symbol -> your exchange symbol)
SYMBOL_MAP = {
    'BTCUSD': 'BTC/USD',
    'ETHUSD': 'ETH/USD',
    'SOLUSD': 'SOL/USD',
    'ADAUSD': 'ADA/USD',
    'XRPUSD': 'XRP/USD',
    'DOTUSD': 'DOT/USD',
    'DOGEUSD': 'DOGE/USD',
    'LINKUSD': 'LINK/USD',
    'MATICUSD': 'MATIC/USD',
    'AVAXUSD': 'AVAX/USD',
    'EURUSD': 'EURUSD=X',
    'GBPUSD': 'GBPUSD=X',
    'USDJPY': 'USDJPY=X',
}

def map_symbol(tv_symbol):
    """Convert TradingView symbol to your exchange format"""
    if tv_symbol in SYMBOL_MAP:
        return SYMBOL_MAP[tv_symbol]
    # Try common formats
    if tv_symbol.endswith('USD') and len(tv_symbol) > 3:
        base = tv_symbol[:-3]
        return f"{base}/USD"
    return tv_symbol

@app.route('/webhook', methods=['POST'])
def webhook():
    """Receive alerts from TradingView"""
    try:
        # Get the alert data
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.get('message')
            if data:
                data = json.loads(data)
            else:
                data = request.data.decode('utf-8')
                if data:
                    data = json.loads(data)
        
        logger.info(f"📡 Received alert: {data}")
        
        # Process in background thread (don't block)
        thread = threading.Thread(target=process_alert, args=(data,))
        thread.daemon = True
        thread.start()
        
        return jsonify({"status": "received"}), 200
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

def process_alert(data):
    """Process the alert in background"""
    try:
        # Extract basic info
        tv_symbol = data.get('symbol', '')
        alert_type = data.get('type', 'unknown')
        event = data.get('event', '')
        price = float(data.get('price', 0))
        
        if not tv_symbol:
            logger.warning("No symbol in alert")
            return
        
        # Map to your symbol format
        symbol = map_symbol(tv_symbol)
        logger.info(f"Processing {alert_type} alert for {symbol}")
        
        # Fetch current data
        candles = None
        
        # Try different exchanges based on symbol
        if 'USD' in symbol and not '=X' in symbol:
            # Crypto - try Kraken first
            candles = bot.exchange_manager.fetch_ohlcv_kraken(symbol, "1h", 200)
            exchange = 'kraken'
            
            if not candles or len(candles) < 100:
                # Try Binance
                candles = bot.exchange_manager.fetch_ohlcv_binanceus(symbol, "1h", 200)
                exchange = 'binanceus'
        else:
            # Forex
            candles = bot.exchange_manager.fetch_forex_yahoo(symbol, "1h", 200)
            exchange = 'yahoo_finance'
        
        if not candles or len(candles) < 100:
            logger.warning(f"Could not fetch data for {symbol}")
            return
        
        # Run your existing analysis
        result = bot.batch_analyzer.process_single_symbol(
            AnalysisTask(
                symbol_key=f"alert:{symbol}",
                exchange=exchange,
                symbol=symbol,
                candles=candles,
                timeframe="1h"
            )
        )
        
        # Check for TCT setups
        if result.tct_setups:
            for setup in result.tct_setups:
                # Add alert context to the setup
                setup['alert_trigger'] = {
                    'type': alert_type,
                    'event': event,
                    'price': price
                }
                
                # Send if confidence is high
                if setup.get('confidence', 0) > 0.75:
                    bot.notifier.send_signal(setup)
                    logger.info(f"✅ Sent TCT signal for {symbol} (conf: {setup.get('confidence', 0):.2f})")
        
        # Check for Wyckoff setups
        if result.wyckoff_schematic and result.wyckoff_schematic.is_valid:
            if result.wyckoff_schematic.confidence > 0.75:
                # Convert to dict for sending
                wyckoff_dict = {
                    "type": "WYCKOFF",
                    "symbol": symbol,
                    "exchange": exchange,
                    "timeframe": "1h",
                    "confidence": result.wyckoff_schematic.confidence,
                    "phase": result.wyckoff_schematic.phase.value if hasattr(result.wyckoff_schematic.phase, 'value') else str(result.wyckoff_schematic.phase),
                    "schematic_type": result.wyckoff_schematic.type.value if hasattr(result.wyckoff_schematic.type, 'value') else str(result.wyckoff_schematic.type),
                    "entry_long": result.wyckoff_schematic.entry_long,
                    "stop_long": result.wyckoff_schematic.stop_long,
                    "target_long": result.wyckoff_schematic.target_long,
                    "entry_short": result.wyckoff_schematic.entry_short,
                    "stop_short": result.wyckoff_schematic.stop_short,
                    "target_short": result.wyckoff_schematic.target_short,
                    "alert_trigger": {
                        'type': alert_type,
                        'event': event,
                        'price': price
                    }
                }
                bot.notifier.send_signal(wyckoff_dict)
                logger.info(f"✅ Sent Wyckoff signal for {symbol} (conf: {result.wyckoff_schematic.confidence:.2f})")
        
        # Also send a confirmation that alert was received
        confirmation_msg = f"""
📡 <b>ALERT RECEIVED</b>
━━━━━━━━━━━━━━━━━━━━
<b>Symbol:</b> {symbol}
<b>Type:</b> {alert_type}
<b>Event:</b> {event}
<b>Price:</b> {price}

<b>Status:</b> Analysis complete
<b>Setups found:</b> {len(result.tct_setups)}
<b>Wyckoff:</b> {'Yes' if result.wyckoff_schematic and result.wyckoff_schematic.is_valid else 'No'}

<i>High confidence signals sent separately</i>
━━━━━━━━━━━━━━━━━━━━
"""
        bot.notifier.send_message(confirmation_msg)
        
    except Exception as e:
        logger.error(f"Error in process_alert: {e}")
        import traceback
        traceback.print_exc()

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "running", "time": datetime.now().isoformat()}), 200

if __name__ == '__main__':
    logger.info("🚀 Webhook server starting...")
    # Use Railway's PORT environment variable or default to 80
    port = int(os.environ.get('PORT', 80))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
