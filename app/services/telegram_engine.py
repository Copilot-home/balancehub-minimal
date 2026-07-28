import asyncio
semaphore = asyncio.Semaphore(2)
import os
import re
import json
import logging
import asyncio
from typing import Dict, Any, Optional

from telethon import TelegramClient, events
from pydantic_settings import BaseSettings, SettingsConfigDict

# 1. Configuration & Validation Layer
class TelegramSettings(BaseSettings):
    TELEGRAM_API_ID: Optional[int] = None
    TELEGRAM_API_HASH: Optional[str] = None
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_TARGET_CHANNEL: Optional[str] = "-1003766302070"  # Target APO Top Deals 🔥
    AFFILIATE_TAG: Optional[str] = "uu4rz3wmhr"  # Shopee Affiliate ID extracted from Email
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = TelegramSettings()
logger = logging.getLogger("APO_Telegram_Engine")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - [%(levelname)s] - %(name)s - %(message)s"))
if not logger.handlers:
    logger.addHandler(handler)

# 2. MTProto Ingestion Layer (Source)
class MTProtoSource:
    """Uses Telethon to connect to MTProto and stream incoming messages."""
    def __init__(self, api_id: int, api_hash: str, session_file: str = "apo_mtproto_session"):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_file = session_file
        self.client = TelegramClient(self.session_file, self.api_id, self.api_hash)

    async def start(self, callback_handler):
        logger.info("Initializing MTProto Core [telethon]...")
        await self.client.start()
        logger.info("✅ MTProto Authenticated! Listening to incoming stream...")
        
        @self.client.on(events.NewMessage(outgoing=False))
        async def handler(event):
            # Pass event to the agent processor middleware
            await callback_handler(event)
            
        await self.client.run_until_disconnected()

# 3. Agent Processing Middleware (Transformation)
class AgentProcessor:
    """Evaluates raw messages and assigns Deal Score F(q). Injects Affiliate logic."""
    def __init__(self, affiliate_tag: str):
        self.affiliate_tag = affiliate_tag

    async def parse_and_score(self, raw_text: str) -> Dict[str, Any]:
        """
        Extracts deal info and links. Ensures 1 deal = 1 payload mapping.
        """
        if not raw_text:
            return {"valid": False}
        
        deals = []
        lines = raw_text.split('\n')
        
        for line in lines:
            urls = re.findall(r'(https?://[^\s]+)', line)
            if urls:
                # Basic brand/title extraction (everything before the URL)
                title_part = line.replace(urls[0], '').strip()
                # Clean up residual characters
                title_part = re.sub(r'[^a-zA-Z0-9\s\#\-]', '', title_part).strip()
                if not title_part or len(title_part) < 3:
                    title_part = "SẢN PHẨM HOT"
                
                # Extract discount like 40% or -40%
                discount_match = re.search(r'(\d{1,2}%)', line)
                if not discount_match:
                    discount_match = re.search(r'(\d{1,2}%)', raw_text)
                discount = f"-{discount_match.group(1)}" if discount_match else "GIÁ SỐC"
                
                # Affiliate Binder (FIX_2: replace raw link -> affiliate link)
                clean_url = urls[0].split("?")[0]
                
                # Ensure correct query param concatenation
                separator = "&" if "?" in clean_url else "?"
                # AFFILIATE_TAG already starts with `?` or `&` based on .env config usually.
                # E.g. `?tag=my_affiliate_tag-20`. So we attach it raw if no query params exist.
                # But to be safe if tag config is just `tag=...`:
                affix = self.affiliate_tag
                if "=" not in affix and not affix.startswith("?"):
                    aff_link = f"{clean_url}?aff_id={affix}&sub_id={affix}"
                elif affix.startswith("?"):
                    aff_link = f"{clean_url}{affix}"
                else:
                    aff_link = f"{clean_url}?{affix}"
                
                brand_name = title_part[:40].strip()
                
                deals.append({
                    "brand": brand_name.upper(),
                    "discount": discount,
                    "affiliate_link": aff_link
                })
        
        # Fallback if structure is inline without newlines
        if not deals:
            urls = re.findall(r'(https?://[^\s]+)', raw_text)
            if not urls:
                return {"valid": False, "reason": "No URLs found"}
            for url in urls:
                clean_url = url.split("?")[0]
                affix = self.affiliate_tag
                if "=" not in affix and not affix.startswith("?"):
                    aff_link = f"{clean_url}?aff_id={affix}&sub_id={affix}"
                elif affix.startswith("?"):
                    aff_link = f"{clean_url}{affix}"
                else:
                    aff_link = f"{clean_url}?{affix}"
                discount_match = re.search(r'(\d{1,2}%)', raw_text)
                discount = f"-{discount_match.group(1)}" if discount_match else "GIÁ SỐC"
                deals.append({
                    "brand": "SẢN PHẨM HOT",
                    "discount": discount,
                    "affiliate_link": aff_link
                })

        # Heuristic scoring
        discount_found = "sale" in raw_text.lower() or "%" in raw_text or bool(deals)
        
        return {
            "valid": True,
            "original_text": raw_text,
            "deals": deals,
            "is_deal": discount_found,
            "score": 8.0 if discount_found else 5.0
        }

# 4. Bot API Dispatch Layer (Sink)
class BotAPIDispatcher:
    """Uses the Telegram Bot API (HTTP) to securely publish deals to a channel."""
    def __init__(self, bot_token: str, target_chat: str):
        self.bot_token = bot_token
        self.target_chat = target_chat
        import httpx
        self.http_client = httpx.AsyncClient()

    async def publish(self, payload: Dict[str, Any]):
        """Publish the finalized deal directly via the Bot API."""
        if not payload.get("valid") or not payload.get("is_deal"):
            logger.info("⏭️ Skipped publishing: Low score or invalid deal.")
            return

        deals = payload.get("deals", [])
        
        # FIX_1 (MANDATORY): 1 deal = 1 post
        for deal in deals:
            brand = deal.get("brand", "HOT")
            discount = deal.get("discount", "")
            aff_link = deal.get("affiliate_link", "")
            
            # FIX_3 (MANDATORY): add CTA (click trigger) & enforce EXACT template
            message_body = (
                f"🔥 {brand} {discount}\n"
                f"💳 Mua ngay: {aff_link}\n"
                f"⏰ Khoảng thời gian Sale rất ngắn!"
            )
            
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            data = {
                "chat_id": self.target_chat,
                "text": message_body,
                "disable_web_page_preview": False
            }
            
            try:
                async with semaphore:
                    response = await self.http_client.post(url, json=data)
                    if response.status_code == 429:
                        retry = int(response.json().get("parameters", {}).get("retry_after", 5))
                        await asyncio.sleep(retry)
                        return
                if response.status_code == 200:
                    logger.info(f"✅ Deal successfully distributed via Bot API Sink to {self.target_chat}.")
                else:
                    logger.error(f"🚨 Bot API Sink Error: {response.text}")
                await asyncio.sleep(1.5)  # Throttle
            except Exception as e:
                logger.error(f"🚨 Bot API Network Error: {e}")

# 5. Core Orchestrator (The Dual Engine Loop)
async def main_loop():
    logger.info("🚀 Initiating TELEGRAM_CORE_APO_EXECUTION_SYSTEM (Full Autonomous Mode)...")
    
    # 5.1 Pre-flight validations
    if not settings.TELEGRAM_API_ID or not settings.TELEGRAM_API_HASH:
        logger.error("❌ CRITICAL: Missing TELEGRAM_API_ID or TELEGRAM_API_HASH.")
        return

    # 5.2 Initialize Layers
    source = MTProtoSource(api_id=settings.TELEGRAM_API_ID, api_hash=settings.TELEGRAM_API_HASH)
    
    # We must ensure the client is connected early so we can pass it to the sink
    await source.client.connect()
    
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("❌ CRITICAL: Missing TELEGRAM_BOT_TOKEN for Bot API Dispatcher.")
        return

    processor = AgentProcessor(affiliate_tag=settings.AFFILIATE_TAG)
    sink = BotAPIDispatcher(bot_token=settings.TELEGRAM_BOT_TOKEN, target_chat=settings.TELEGRAM_TARGET_CHANNEL)

    # 5.3 Bridging Logic
    async def incoming_message_bridge(event):
        try:
            # Check source channel, etc (For now, process all incoming, or filter by specific channel ID)
            raw_text = event.raw_text
            if not raw_text: return
            
            logger.info("📥 Captured MTProto message, routing to Agent Processor...")
            payload = await processor.parse_and_score(raw_text)
            
            if payload.get("valid"):
                logger.info(f"🧠 Deal Scored: {payload['score']} - Forwarding to Sink...")
                await sink.publish(payload)
                
        except Exception as e:
            logger.error(f"🚨 Pipeline failure during event processing: {e}")

    # 5.4 Execute Pipeline
    try:
        await source.start(incoming_message_bridge)
    except KeyboardInterrupt:
        logger.info("🛑 APΩ System safely shutting down.")

if __name__ == "__main__":
    asyncio.run(main_loop())
semaphore = asyncio.Semaphore(2)
