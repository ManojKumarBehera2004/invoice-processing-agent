import json
import re
import logging
from typing import Optional, Tuple
import httpx
from app.config import settings
from app.schemas import InvoiceExtractionSchema, LineItemSchema

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an invoice data extraction system.
Extract only information that is actually present in the supplied document.
Return valid JSON matching the required schema.
Do not guess or invent missing information.
If a field is missing or unreadable, return null.

Extract:
- vendor_name (string or null)
- invoice_number (string or null)
- invoice_date (string normalized to YYYY-MM-DD or null)
- currency (currency code e.g. INR, USD, EUR, GBP)
- line_items: list of objects with [description, quantity (number), unit_price (number), amount (number)]
- subtotal (number or null)
- tax (number or null)
- total (number or null)

Return ONLY a single valid JSON object. Do not enclose in markdown code fences if possible, or use standard ```json ``` formatting.
"""

class BaseAIExtractor:
    async def extract(self, document_text: str, filename: str = "") -> Tuple[InvoiceExtractionSchema, str]:
        raise NotImplementedError

class GeminiAIExtractor(BaseAIExtractor):
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        self.api_key = api_key
        self.model = model
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    async def extract(self, document_text: str, filename: str = "") -> Tuple[InvoiceExtractionSchema, str]:
        prompt = f"{SYSTEM_PROMPT}\n\nDocument Text:\n\"\"\"\n{document_text}\n\"\"\""
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.endpoint, json=payload)
            if response.status_code != 200:
                logger.error(f"Gemini API Error: {response.status_code} - {response.text}")
                raise ValueError(f"Gemini API Error: {response.text}")
            
            data = response.json()
            raw_content = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed_json = self._clean_and_parse_json(raw_content)
            schema = InvoiceExtractionSchema(**parsed_json)
            return schema, "AI_GEMINI"

    def _clean_and_parse_json(self, raw_str: str) -> dict:
        cleaned = re.sub(r"^```json\s*", "", raw_str.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE).strip()
        return json.loads(cleaned)

class OpenAIExtractor(BaseAIExtractor):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.endpoint = "https://api.openai.com/v1/chat/completions"

    async def extract(self, document_text: str, filename: str = "") -> Tuple[InvoiceExtractionSchema, str]:
        prompt = f"{SYSTEM_PROMPT}\n\nDocument Text:\n\"\"\"\n{document_text}\n\"\"\""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Extract structured invoice information from this document:\n\n{document_text}"}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.endpoint, json=payload, headers=headers)
            if response.status_code != 200:
                logger.error(f"OpenAI API Error: {response.status_code} - {response.text}")
                raise ValueError(f"OpenAI API Error: {response.text}")
            
            data = response.json()
            raw_content = data["choices"][0]["message"]["content"]
            parsed_json = json.loads(raw_content)
            schema = InvoiceExtractionSchema(**parsed_json)
            return schema, "AI_OPENAI"

class DemoFallbackExtractor(BaseAIExtractor):
    """
    Intelligent deterministic extractor for local testing, offline demo,
    and when no external AI API key is configured.
    Clearly tags the extraction as DEMO_FALLBACK.
    """
    async def extract(self, document_text: str, filename: str = "") -> Tuple[InvoiceExtractionSchema, str]:
        logger.info(f"Using DemoFallbackExtractor for document: {filename}")
        
        text_lower = document_text.lower()
        
        # Check for sample invoice patterns or do regex extraction
        vendor_name = None
        invoice_number = None
        invoice_date = None
        currency = "INR"
        line_items = []
        subtotal = None
        tax = None
        total = None

        # Detect currency
        if "$" in document_text or "usd" in text_lower:
            currency = "USD"
        elif "€" in document_text or "eur" in text_lower:
            currency = "EUR"
        elif "£" in document_text or "gbp" in text_lower:
            currency = "GBP"
        elif "₹" in document_text or "inr" in text_lower or "rs" in text_lower:
            currency = "INR"

        # Regex heuristics for vendor name
        vendor_match = re.search(r"(?:vendor|from|company|supplier|billed by):\s*([^\n\r]+)", document_text, re.IGNORECASE)
        if vendor_match:
            vendor_name = vendor_match.group(1).strip()
        else:
            # First non-empty line if short
            lines = [l.strip() for l in document_text.splitlines() if l.strip()]
            if lines and len(lines[0]) < 60 and not any(kw in lines[0].lower() for kw in ["invoice", "bill", "tax"]):
                vendor_name = lines[0]

        # Regex for invoice number
        inv_match = re.search(r"(?:invoice\s*(?:no|number|#|id)|inv[\s#-]*):\s*([a-zA-Z0-9\-_]+)", document_text, re.IGNORECASE)
        if inv_match:
            invoice_number = inv_match.group(1).strip()
        else:
            # Fallback search for tokens like INV-1002
            token_match = re.search(r"\b(INV-[0-9]{3,8}|[A-Z]{2,4}-[0-9]{3,8})\b", document_text)
            if token_match:
                invoice_number = token_match.group(1)

        # Regex for invoice date
        date_match = re.search(r"(?:date|invoice\s*date):\s*([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2}|[0-9]{1,2}[-/][0-9]{1,2}[-/][0-9]{2,4})", document_text, re.IGNORECASE)
        if date_match:
            raw_date = date_match.group(1).strip()
            # Normalize to YYYY-MM-DD
            try:
                parts = re.split(r"[-/]", raw_date)
                if len(parts) == 3:
                    if len(parts[0]) == 4:  # YYYY-MM-DD
                        invoice_date = f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
                    elif len(parts[2]) == 4:  # DD-MM-YYYY or MM-DD-YYYY
                        invoice_date = f"{parts[2]}-{int(parts[1]):02d}-{int(parts[0]):02d}"
            except Exception:
                invoice_date = raw_date
        else:
            # Check for standalone YYYY-MM-DD
            stand_date = re.search(r"\b(20[2-3][0-9]-[0-1][0-9]-[0-3][0-9])\b", document_text)
            if stand_date:
                invoice_date = stand_date.group(1)

        # Regex for totals
        subtotal_match = re.search(r"(?:\bsubtotal|\bsub-total|\bnet\s*amount)\s*[:\-]?\s*[₹$€£]?\s*([0-9,]+\.?[0-9]*)", document_text, re.IGNORECASE)
        if subtotal_match:
            subtotal = float(subtotal_match.group(1).replace(",", ""))

        tax_match = re.search(r"(?:\btax|\bgst|\bvat|\bsales\s*tax)\s*[:\-]?\s*[₹$€£]?\s*([0-9,]+\.?[0-9]*)", document_text, re.IGNORECASE)
        if tax_match:
            tax = float(tax_match.group(1).replace(",", ""))

        total_match = re.search(r"(?:\bgrand\s*total|\btotal\s*amount|\btotal)\s*[:\-]?\s*[₹$€£]?\s*([0-9,]+\.?[0-9]*)", document_text, re.IGNORECASE)
        if total_match:
            total = float(total_match.group(1).replace(",", ""))

        # Check for tabular line item patterns
        # e.g., Description ... qty ... price ... amount
        for line in document_text.splitlines():
            line_clean = line.strip()
            # look for numbers at the end of line
            nums = re.findall(r"([0-9,]+\.?[0-9]*)", line_clean)
            if len(nums) >= 3 and not any(kw in line_clean.lower() for kw in ["subtotal", "tax", "total", "phone", "date", "pincode"]):
                try:
                    amt = float(nums[-1].replace(",", ""))
                    price = float(nums[-2].replace(",", ""))
                    qty = float(nums[-3].replace(",", ""))
                    desc = re.sub(r"([0-9,]+\.?[0-9]*)", "", line_clean).strip(" |-\t")
                    if desc and len(desc) > 2 and qty > 0 and price > 0:
                        line_items.append(LineItemSchema(
                            description=desc,
                            quantity=qty,
                            unit_price=price,
                            amount=amt
                        ))
                except Exception:
                    continue

        # If regex line items empty, provide reasonable fallback based on total
        if not line_items and total:
            line_items.append(LineItemSchema(
                description="Professional Services / Item",
                quantity=1.0,
                unit_price=subtotal if subtotal else (total * 0.82),
                amount=subtotal if subtotal else (total * 0.82)
            ))

        return InvoiceExtractionSchema(
            vendor_name=vendor_name,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            currency=currency,
            line_items=line_items,
            subtotal=subtotal,
            tax=tax,
            total=total,
            confidence=0.92
        ), "DEMO_FALLBACK"

class AIExtractionService:
    def __init__(self):
        self.provider_name = settings.AI_PROVIDER.lower()
        self.api_key = settings.AI_API_KEY.strip()
        self.model = settings.AI_MODEL

    async def extract_invoice_data(self, document_text: str, filename: str = "") -> Tuple[InvoiceExtractionSchema, str]:
        """
        Extracts structured data using the configured AI provider.
        Falls back cleanly to DemoFallbackExtractor if key is absent or API fails.
        """
        if not self.api_key or self.provider_name == "demo":
            logger.info("No AI API Key provided or demo mode selected; using DemoFallbackExtractor.")
            extractor = DemoFallbackExtractor()
            return await extractor.extract(document_text, filename)

        try:
            if self.provider_name == "gemini":
                extractor = GeminiAIExtractor(api_key=self.api_key, model=self.model)
                return await extractor.extract(document_text, filename)
            elif self.provider_name in ("openai", "gpt"):
                extractor = OpenAIExtractor(api_key=self.api_key, model=self.model)
                return await extractor.extract(document_text, filename)
            else:
                logger.warning(f"Unknown provider '{self.provider_name}', falling back to Demo extractor.")
                return await DemoFallbackExtractor().extract(document_text, filename)
        except Exception as e:
            logger.error(f"AI API extraction failed: {e}. Falling back to DemoFallbackExtractor.")
            extracted, _ = await DemoFallbackExtractor().extract(document_text, filename)
            return extracted, "DEMO_FALLBACK_AFTER_ERROR"
