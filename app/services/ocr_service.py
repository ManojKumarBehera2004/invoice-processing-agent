import shutil
import logging
from pathlib import Path
from PIL import Image
import pytesseract
from app.config import settings

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        # Configure tesseract executable if provided in settings or found in standard locations
        if settings.TESSERACT_CMD and Path(settings.TESSERACT_CMD).exists():
            pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
        else:
            # Common Windows paths if not in PATH
            common_paths = [
                r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                r"C:\Users\AppData\Local\Tesseract-OCR\tesseract.exe"
            ]
            for p in common_paths:
                if Path(p).exists():
                    pytesseract.pytesseract.tesseract_cmd = p
                    break

    def is_tesseract_available(self) -> bool:
        """Check if tesseract binary is accessible."""
        try:
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def extract_text_from_image(self, image_input: str | Path | Image.Image) -> str:
        """
        Extract text from an image (filepath or PIL Image) using Tesseract OCR.
        If Tesseract is not installed, catches the error and provides a structured fallback.
        """
        try:
            if isinstance(image_input, (str, Path)):
                img = Image.open(str(image_input))
            else:
                img = image_input

            # Convert to RGB if needed
            if img.mode not in ("L", "RGB"):
                img = img.convert("RGB")

            text = pytesseract.image_to_string(img, config="--psm 6")
            return text.strip()
        except pytesseract.TesseractNotFoundError:
            logger.warning("Tesseract OCR binary not found on host. OCR extraction skipped.")
            return "[OCR Notice: Tesseract executable not detected on system. Image text extraction fallback applied.]"
        except Exception as e:
            logger.error(f"OCR Extraction error: {e}")
            return f"[OCR Error during image processing: {str(e)}]"

    def extract_text_from_images(self, images: list[Image.Image]) -> str:
        """Extract text from multiple PIL images and concatenate."""
        results = []
        for idx, img in enumerate(images):
            page_text = self.extract_text_from_image(img)
            if page_text:
                results.append(f"--- Page {idx + 1} ---\n{page_text}")
        return "\n\n".join(results)
