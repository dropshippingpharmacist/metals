#!/usr/bin/env python3
"""
TELEGRAM → DISCORD SIGNAL FORWARDER
For Stocks, Indices, Commodities, Metals & Oil (No Crypto)
Run this as a separate script (python3 forwarder.py)
It will monitor your Telegram channel and forward signals to Discord
"""

import time
import requests
import re
from datetime import datetime
from typing import Set, Dict, List, Optional

# =============================================================================
# CONFIGURATION
# =============================================================================
TELEGRAM_BOT_TOKEN = "8335392741:AAGd0nMObLGljLleORQ9j-rCw9pW6vEqnLw"
TELEGRAM_CHAT_ID = "5747777199"  # Only this chat ID
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1469423344842572012/Mrumq0xtG0XL-nFcgi6iqi3Q60KB80Tb5fi1fZqm1msJ0cGS0fVKtkvaNsh7MAmz2sv3"

# Asset categories (for filtering and display)
ASSET_CATEGORIES = {
    "Forex": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD",
              "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "CHFJPY", "EURAUD"],
    "Indices": ["SPX500", "NAS100", "UK100", "GER30", "FRA40", "JPN225", "SPX", "NAS", "DOW"],
    "Metals": ["XAUUSD", "XAGUSD", "GOLD", "SILVER"],
    "Commodities": ["XCUUSD", "COPPER", "PLATINUM", "XPTUSD"],
    "Oil": ["BCOUSD", "WTICOUSD", "BRENT", "WTI", "OIL"]
}

# =============================================================================
# DISCORD SENDER
# =============================================================================
class DiscordSender:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.last_signal_time = 0
        self.min_interval_seconds = 30  # Minimum 30 seconds between signals
    
    def _extract_symbol(self, message_text: str) -> str:
        """Extract trading symbol from message"""
        # Look for common symbol patterns
        patterns = [
            r'([A-Z]{3,6}/[A-Z]{3})',  # EUR/USD format
            r'([A-Z]{3,6}_[A-Z]{3})',  # EUR_USD format
            r'([A-Z]{3,6}\s+[A-Z]{3})',  # EUR USD format
            r'\*\*([A-Z]{3,6})\*\*',  # **EURUSD**
            r'([A-Z]{3,6})(?=\s+(?:LONG|SHORT))',  # EURUSD LONG
            r'([A-Z]{3,6})(?=\s+Entry:)',  # EURUSD Entry:
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message_text, re.IGNORECASE)
            if match:
                symbol = match.group(1).replace('/', '_').replace(' ', '_')
                return symbol.upper()
        
        # Default: try to find any 6-character symbol
        words = message_text.split()
        for word in words:
            word_clean = re.sub(r'[^\w/]', '', word.upper())
            if len(word_clean) >= 5 and len(word_clean) <= 7 and '/' in word_clean:
                return word_clean.replace('/', '_')
            elif len(word_clean) == 6 and word_clean.isalpha():
                return word_clean
        
        return "Unknown"
    
    def _get_asset_category(self, symbol: str) -> str:
        """Determine asset category from symbol"""
        symbol_upper = symbol.upper()
        
        for category, symbols in ASSET_CATEGORIES.items():
            for s in symbols:
                if s in symbol_upper:
                    return category
        
        # Default based on symbol patterns
        if 'USD' in symbol_upper or 'GBP' in symbol_upper or 'EUR' in symbol_upper:
            return "Forex"
        elif 'XAU' in symbol_upper or 'GOLD' in symbol_upper:
            return "Metals"
        elif 'XAG' in symbol_upper or 'SILVER' in symbol_upper:
            return "Metals"
        elif 'OIL' in symbol_upper or 'BRENT' in symbol_upper or 'WTI' in symbol_upper:
            return "Oil"
        elif 'SPX' in symbol_upper or 'NAS' in symbol_upper or 'DOW' in symbol_upper:
            return "Indices"
        
        return "Other"
    
    def _parse_signal_fields(self, message_text: str) -> Dict:
        """Parse the message to extract all signal fields"""
        fields = {
            "symbol": "",
            "direction": "",
            "entry": "",
            "stop": "",
            "target": "",
            "tp1": "",
            "tp2": "",
            "tp3": "",
            "rr": "",
            "confidence": "",
            "ltf": ""
        }
        
        lines = message_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            line_lower = line.lower()
            
            # Detect direction from emoji or text
            if '🟢' in line or 'long' in line_lower:
                fields["direction"] = "LONG"
            elif '🔴' in line or 'short' in line_lower:
                fields["direction"] = "SHORT"
            
            # Extract symbol (first line often contains symbol)
            if not fields["symbol"] and ('🟢' in line or '🔴' in line or 'long' in line_lower or 'short' in line_lower):
                # Remove emoji and direction words
                clean = re.sub(r'[🟢🔴]', '', line)
                clean = re.sub(r'\b(LONG|SHORT)\b', '', clean, flags=re.IGNORECASE)
                clean = clean.strip()
                if clean:
                    fields["symbol"] = clean
            
            # Extract fields using regex
            entry_match = re.search(r'Entry:\s*([\d.]+)', line, re.IGNORECASE)
            if entry_match:
                fields["entry"] = entry_match.group(1)
            
            stop_match = re.search(r'Stop:\s*([\d.]+)', line, re.IGNORECASE)
            if stop_match:
                fields["stop"] = stop_match.group(1)
            
            target_match = re.search(r'Target:\s*([\d.]+)', line, re.IGNORECASE)
            if target_match:
                fields["target"] = target_match.group(1)
            
            tp1_match = re.search(r'TP1:\s*([\d.]+)', line, re.IGNORECASE)
            if tp1_match:
                fields["tp1"] = tp1_match.group(1)
            
            tp2_match = re.search(r'TP2:\s*([\d.]+)', line, re.IGNORECASE)
            if tp2_match:
                fields["tp2"] = tp2_match.group(1)
            
            tp3_match = re.search(r'TP3:\s*([\d.]+)', line, re.IGNORECASE)
            if tp3_match:
                fields["tp3"] = tp3_match.group(1)
            
            rr_match = re.search(r'R:R\s*([\d.]+)', line, re.IGNORECASE)
            if rr_match:
                fields["rr"] = rr_match.group(1)
            
            conf_match = re.search(r'Conf:\s*(\d+)%', line, re.IGNORECASE)
            if conf_match:
                fields["confidence"] = conf_match.group(1)
            
            ltf_match = re.search(r'LTF:\s*(\w+)', line, re.IGNORECASE)
            if ltf_match:
                fields["ltf"] = ltf_match.group(1)
        
        # If symbol still not found, try to extract from first line
        if not fields["symbol"] and lines:
            first_line = lines[0].strip()
            first_line = re.sub(r'[🟢🔴]', '', first_line)
            first_line = re.sub(r'\b(LONG|SHORT)\b', '', first_line, flags=re.IGNORECASE)
            fields["symbol"] = first_line.strip()
        
        return fields
    
    def _format_price(self, price: str) -> str:
        """Format price for display"""
        try:
            p = float(price)
            if p > 1000:
                return f"${p:,.2f}"
            elif p > 1:
                return f"${p:.4f}"
            else:
                return f"${p:.6f}"
        except:
            return price
    
    def send_signal(self, message_text: str, original_date: datetime = None) -> bool:
        """Send formatted signal to Discord"""
        
        # Rate limiting
        current_time = time.time()
        if current_time - self.last_signal_time < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - (current_time - self.last_signal_time))
        self.last_signal_time = time.time()
        
        timestamp = original_date.strftime("%Y-%m-%d %H:%M:%S") if original_date else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Parse signal fields
        fields = self._parse_signal_fields(message_text)
        
        # Get symbol and category
        symbol = fields["symbol"]
        if not symbol:
            symbol = self._extract_symbol(message_text)
        
        category = self._get_asset_category(symbol)
        
        # Determine signal type and colors
        is_long = fields["direction"] == "LONG" or "🟢" in message_text
        is_short = fields["direction"] == "SHORT" or "🔴" in message_text
        
        if is_long:
            direction = "LONG"
            color = 0x00ff00
            emoji = "🟢"
        elif is_short:
            direction = "SHORT"
            color = 0xff0000
            emoji = "🔴"
        else:
            direction = "SIGNAL"
            color = 0x00aaff
            emoji = "📊"
        
        # Category emoji
        category_emojis = {
            "Forex": "💱",
            "Indices": "📈",
            "Metals": "🥇",
            "Commodities": "📦",
            "Oil": "🛢️",
            "Other": "📊"
        }
        category_emoji = category_emojis.get(category, "📊")
        
        # Build Discord embed
        embed_fields = []
        
        # Add formatted fields
        if fields["entry"]:
            embed_fields.append({"name": "💰 Entry", "value": self._format_price(fields["entry"]), "inline": True})
        if fields["stop"]:
            embed_fields.append({"name": "🛑 Stop Loss", "value": self._format_price(fields["stop"]), "inline": True})
        if fields["target"]:
            embed_fields.append({"name": "🎯 Target", "value": self._format_price(fields["target"]), "inline": True})
        if fields["tp1"]:
            embed_fields.append({"name": "🎯 TP1", "value": self._format_price(fields["tp1"]), "inline": True})
        if fields["tp2"]:
            embed_fields.append({"name": "🎯 TP2", "value": self._format_price(fields["tp2"]), "inline": True})
        if fields["tp3"]:
            embed_fields.append({"name": "🎯 TP3", "value": self._format_price(fields["tp3"]), "inline": True})
        if fields["rr"]:
            embed_fields.append({"name": "📊 R:R", "value": f"1:{fields['rr']}", "inline": True})
        if fields["confidence"]:
            embed_fields.append({"name": "🎯 Confidence", "value": f"{fields['confidence']}%", "inline": True})
        if fields["ltf"]:
            embed_fields.append({"name": "⏱️ Timeframe", "value": fields["ltf"], "inline": True})
        
        # Create the embed
        title = f"{emoji} {direction} {symbol} {category_emoji}"
        
        embed = {
            "title": title,
            "description": f"**{category}** • {emoji} {direction} Signal",
            "color": color,
            "fields": embed_fields,
            "footer": {"text": f"Received: {timestamp} • Pure Strategy"},
            "timestamp": datetime.now().isoformat()
        }
        
        # If we couldn't parse fields, just send the raw message
        if not embed_fields:
            embed = {
                "title": title,
                "description": f"```\n{message_text}\n```",
                "color": color,
                "footer": {"text": f"Received: {timestamp} • Pure Strategy"}
            }
        
        payload = {
            "embeds": [embed],
            "username": "📊 Signal Bot",
            "avatar_url": "https://cdn-icons-png.flaticon.com/512/906/906334.png"
        }
        
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            if response.status_code in [200, 204]:
                print(f"   ✅ Forwarded to Discord: {symbol} ({direction})")
                return True
            else:
                print(f"   ❌ Discord error: {response.status_code} - {response.text[:100]}")
                return False
        except Exception as e:
            print(f"   ❌ Failed: {e}")
            return False


# =============================================================================
# TELEGRAM POLLER
# =============================================================================
class TelegramPoller:
    def __init__(self):
        self.discord = DiscordSender(DISCORD_WEBHOOK_URL)
        self.last_update_id = 0
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.sent_signals: Set[str] = set()
        self.chat_id = TELEGRAM_CHAT_ID
    
    def get_updates(self):
        """Fetch new messages from Telegram"""
        url = f"{self.api_url}/getUpdates"
        params = {
            "offset": self.last_update_id + 1,
            "timeout": 30,
        }
        
        try:
            response = requests.get(url, params=params, timeout=35)
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    return data.get("result", [])
            else:
                print(f"⚠️ Telegram API error: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Error fetching updates: {e}")
        
        return []
    
    def is_signal(self, text: str) -> bool:
        """Check if message is a trading signal from your bot"""
        if not text:
            return False
        
        # Signal indicators
        signal_indicators = ["🟢", "🔴", "LONG", "SHORT", "Stop:", "TP1:", "TP2:", "TP3:", "LTF:", "Conf:", "RR:"]
        
        # Count matches
        matches = sum(1 for indicator in signal_indicators if indicator in text)
        
        # Also check for typical signal format
        has_emoji = "🟢" in text or "🔴" in text
        has_stop = "Stop:" in text
        has_tp = "TP1:" in text or "TP2:" in text or "Target:" in text
        
        return matches >= 3 or (has_emoji and has_stop and has_tp)
    
    def create_unique_id(self, message) -> str:
        """Create unique ID for message to avoid duplicates"""
        text = message.get("text", message.get("caption", ""))
        date = message.get("date", 0)
        chat_id = message.get("chat", {}).get("id", 0)
        return f"{chat_id}_{text[:50]}_{date}"
    
    def process_message(self, message):
        """Process and forward a message"""
        # Get message text
        message_text = message.get("text", "")
        if not message_text:
            message_text = message.get("caption", "")
            if not message_text:
                return
        
        # Get chat info
        chat = message.get("chat", {})
        chat_id = str(chat.get("id", ""))
        
        # Only process messages from our specific chat
        if chat_id != self.chat_id:
            return
        
        # Create unique ID
        msg_id = self.create_unique_id(message)
        
        # Skip if already sent
        if msg_id in self.sent_signals:
            return
        
        # Check if it's a signal
        if self.is_signal(message_text):
            # Get date
            date = datetime.fromtimestamp(message.get("date", datetime.now().timestamp()))
            
            chat_title = chat.get("title", chat.get("username", "Unknown"))
            
            print(f"\n{'='*60}")
            print(f"📨 SIGNAL DETECTED!")
            print(f"   From: {chat_title}")
            print(f"   Time: {date.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   Message: {message_text[:80]}...")
            print(f"{'='*60}")
            
            # Forward to Discord
            if self.discord.send_signal(message_text, date):
                self.sent_signals.add(msg_id)
                
                # Keep only last 500 IDs to prevent memory growth
                if len(self.sent_signals) > 500:
                    self.sent_signals = set(list(self.sent_signals)[-250:])
            else:
                print(f"   ⚠️ Failed to forward")
    
    def run(self):
        """Main loop - poll for new messages"""
        print("\n" + "="*60)
        print("  📡 TELEGRAM → DISCORD SIGNAL FORWARDER")
        print("="*60)
        print(f"  Telegram Bot: Active")
        print(f"  Monitoring Chat ID: {self.chat_id}")
        print(f"  Discord Webhook: Configured")
        print(f"  Status: Waiting for signals...")
        print("="*60 + "\n")
        
        # Send startup message to Discord
        startup_embed = {
            "title": "✅ Signal Forwarder Active",
            "description": "Monitoring Telegram for trading signals...\n\n**Assets Monitored:**\n• Forex 💱\n• Indices 📈\n• Metals 🥇\n• Commodities 📦\n• Oil 🛢️\n\n**Strategy:** Pure (A+ and A setups only)",
            "color": 0x00ff00,
            "footer": {"text": f"Started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
        }
        
        try:
            response = requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [startup_embed]}, timeout=10)
            if response.status_code in [200, 204]:
                print("✅ Startup message sent to Discord")
            else:
                print(f"⚠️ Could not send startup message: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Could not send startup message: {e}")
        
        print("🟢 Forwarder is running! Press Ctrl+C to stop\n")
        
        empty_count = 0
        
        while True:
            try:
                updates = self.get_updates()
                
                if updates:
                    empty_count = 0
                    for update in updates:
                        # Update last_update_id
                        self.last_update_id = update.get("update_id", self.last_update_id)
                        
                        # Process channel_post (messages from channels)
                        if "channel_post" in update:
                            self.process_message(update["channel_post"])
                        
                        # Process regular message
                        elif "message" in update:
                            self.process_message(update["message"])
                else:
                    empty_count += 1
                    # Print heartbeat every 60 empty polls (~2 minutes)
                    if empty_count % 60 == 0 and empty_count > 0:
                        print(f"💓 Listening... (Last signal: {datetime.now().strftime('%H:%M:%S')})")
                
                time.sleep(2)  # Poll every 2 seconds
                
            except KeyboardInterrupt:
                print("\n\n🛑 Forwarder stopped by user")
                
                # Send shutdown message to Discord
                shutdown_embed = {
                    "title": "🛑 Forwarder Stopped",
                    "description": "Signal forwarding has been stopped.",
                    "color": 0xff0000,
                    "footer": {"text": f"Stopped at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
                }
                try:
                    requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [shutdown_embed]}, timeout=10)
                except:
                    pass
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(5)


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║         TELEGRAM → DISCORD SIGNAL FORWARDER                  ║
╠══════════════════════════════════════════════════════════════╣
║  Forwards trading signals from Telegram to Discord          ║
║  Assets: Stocks, Indices, Forex, Metals, Commodities, Oil   ║
║  Strategy: Pure (A+ and A setups only)                  ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    forwarder = TelegramPoller()
    
    try:
        forwarder.run()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
