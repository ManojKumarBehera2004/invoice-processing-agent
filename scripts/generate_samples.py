import os
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont

def generate_pdf(filename: str, text_content: str):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    
    # Header banner
    page.draw_rect(fitz.Rect(0, 0, 595, 60), color=None, fill=(0.12, 0.16, 0.24))
    page.insert_text(fitz.Point(40, 38), "AI AUTOMATED INVOICE SYSTEM", fontsize=16, color=(1, 1, 1))

    # Document body
    y = 100
    for line in text_content.strip().split("\n"):
        line_clean = line.strip()
        if not line_clean:
            y += 12
            continue
        if any(h in line_clean for h in ["INVOICE", "VENDOR:", "ITEMS", "TOTAL"]):
            page.insert_text(fitz.Point(40, y), line_clean, fontsize=12, color=(0.1, 0.2, 0.4))
            y += 20
        else:
            page.insert_text(fitz.Point(50, y), line_clean, fontsize=10, color=(0.2, 0.2, 0.2))
            y += 16

    # Bottom border
    page.draw_line(fitz.Point(40, 780), fitz.Point(555, 780), color=(0.7, 0.7, 0.7), width=1)
    page.insert_text(fitz.Point(40, 800), "Generated for Evaluation - AI Document & Invoice Processing Agent", fontsize=8, color=(0.5, 0.5, 0.5))

    doc.save(filename)
    doc.close()
    print(f"Generated PDF: {filename}")

def generate_image_invoice(filename: str):
    img = Image.new("RGB", (700, 900), color=(250, 250, 252))
    draw = ImageDraw.Draw(img)
    
    # Draw header bar
    draw.rectangle([(0, 0), (700, 70)], fill=(30, 41, 59))
    draw.text((40, 25), "RECEIPT & TAX INVOICE", fill=(255, 255, 255))
    
    text = """
    Vendor: FastTrack Courier & Logistics
    Invoice No: INV-IMG-7744
    Date: 2026-03-21
    Currency: INR
    
    Items:
    Express Air Parcel Freight    Qty: 2    Price: 1500.00    Amt: 3000.00
    Fragile Packaging Service     Qty: 1    Price: 500.00     Amt: 500.00
    
    Subtotal: 3500.00
    Tax (18% GST): 630.00
    Total: 4130.00
    """
    draw.text((40, 110), text, fill=(20, 20, 20))
    img.save(filename)
    print(f"Generated Image: {filename}")

if __name__ == "__main__":
    out_dir = Path("sample_invoices")
    out_dir.mkdir(exist_ok=True)

    # 1. Valid Invoice
    valid_text = """
    INVOICE
    Vendor: CloudScale Infrastructure Solutions
    Invoice No: INV-2026-001
    Date: 2026-03-24
    Currency: INR

    ITEMS:
    Database Managed Cluster | 2 | 20000.00 | 40000.00
    Virtual Private Cloud Gateway | 1 | 10000.00 | 10000.00

    Subtotal: 50000.00
    Tax: 9000.00
    Total: 59000.00
    """
    generate_pdf(str(out_dir / "1_valid_invoice.pdf"), valid_text)

    # 2. Calculation Mismatch
    mismatch_text = """
    INVOICE
    Vendor: Apex Global Network
    Invoice No: INV-2026-002
    Date: 2026-03-22
    Currency: INR

    ITEMS:
    Gigabit Dedicated Fiber Uplink | 1 | 30000.00 | 30000.00

    Subtotal: 30000.00
    Tax: 5400.00
    Total: 45000.00
    """
    generate_pdf(str(out_dir / "2_mismatch_invoice.pdf"), mismatch_text)

    # 3. High-Value Invoice
    highval_text = """
    INVOICE
    Vendor: Quantum High Performance Servers Corp
    Invoice No: INV-2026-003
    Date: 2026-03-25
    Currency: INR

    ITEMS:
    Enterprise GPU Acceleration Node | 1 | 250000.00 | 250000.00

    Subtotal: 250000.00
    Tax: 45000.00
    Total: 295000.00
    """
    generate_pdf(str(out_dir / "3_high_value_invoice.pdf"), highval_text)

    # 4. Missing Fields Invoice
    missing_text = """
    INVOICE
    Invoice No: INV-2026-004
    Date: 2026-03-26
    Currency: INR

    ITEMS:
    Office Modular Desks | 2 | 6000.00 | 12000.00

    Subtotal: 12000.00
    Tax: 2160.00
    Total: 14160.00
    """
    generate_pdf(str(out_dir / "4_missing_vendor_invoice.pdf"), missing_text)

    # 5. PNG image document
    generate_image_invoice(str(out_dir / "5_sample_receipt.png"))
    print("All sample test invoice files created successfully.")
