import pymupdf as fitz
from pathlib import Path
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)

class PDFService:
    @staticmethod
    def extract_text(pdf_path: str) -> tuple[str, bool]:
        """
        Extract text from a PDF file using PyMuPDF.
        Returns:
            (extracted_text, is_scanned)
            is_scanned is True if text extraction yielded negligible characters.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        extracted_text = []
        try:
            doc = fitz.open(str(path))
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                page_text = page.get_text()
                if page_text:
                    extracted_text.append(page_text.strip())
            doc.close()
        except Exception as e:
            logger.error(f"Error reading PDF with PyMuPDF: {e}")
            raise ValueError(f"Failed to parse PDF document: {str(e)}")

        full_text = "\n\n".join(extracted_text).strip()
        
        # If less than 40 non-whitespace characters were extracted from all pages,
        # it is likely a scanned PDF image.
        is_scanned = len("".join(full_text.split())) < 40
        return full_text, is_scanned

    @staticmethod
    def convert_pdf_to_images(pdf_path: str, max_pages: int = 5) -> list[Image.Image]:
        """
        Renders PDF pages as Pillow Image objects for OCR processing.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        images = []
        try:
            doc = fitz.open(str(path))
            pages_to_render = min(len(doc), max_pages)
            for page_num in range(pages_to_render):
                page = doc.load_page(page_num)
                # Render at 200 DPI for high OCR accuracy (zoom = 200/72 ≈ 2.77)
                zoom = 200 / 72
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                images.append(img)
            doc.close()
        except Exception as e:
            logger.error(f"Error rendering PDF pages to images: {e}")
            raise ValueError(f"Failed to render PDF to image: {str(e)}")

        return images
