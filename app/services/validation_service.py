from datetime import datetime
import re
from typing import List
from app.schemas import InvoiceExtractionSchema, ValidationResultSchema, ValidationChecks

class ValidationService:
    TOLERANCE = 0.05  # Currency rounding tolerance

    @classmethod
    def validate_invoice(cls, data: InvoiceExtractionSchema) -> ValidationResultSchema:
        checks = ValidationChecks()
        errors: List[str] = []
        warnings: List[str] = []

        # ----------------- Check A: Required Fields -----------------
        missing_fields = []
        if not data.vendor_name or not data.vendor_name.strip():
            missing_fields.append("Vendor Name")
        if not data.invoice_number or not data.invoice_number.strip():
            missing_fields.append("Invoice Number")
        if not data.invoice_date or not data.invoice_date.strip():
            missing_fields.append("Invoice Date")
        if data.total is None or data.total <= 0:
            missing_fields.append("Total Amount")

        if missing_fields:
            checks.required_fields = "FAIL"
            errors.append(f"Missing mandatory fields: {', '.join(missing_fields)}")

        # ----------------- Check B: Date Validation -----------------
        if data.invoice_date:
            date_valid = False
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"):
                try:
                    parsed_date = datetime.strptime(data.invoice_date.strip(), fmt)
                    # Year sanity check (between 1990 and 2050)
                    if 1990 <= parsed_date.year <= 2050:
                        date_valid = True
                        break
                except ValueError:
                    continue

            if not date_valid:
                checks.date = "FAIL"
                errors.append(f"Invalid date format or value: '{data.invoice_date}'. Expected valid YYYY-MM-DD.")
        else:
            checks.date = "FAIL"

        # ----------------- Check C: Line Item Calculation -----------------
        items_valid = True
        calc_line_sum = 0.0

        if data.line_items:
            for idx, item in enumerate(data.line_items, start=1):
                expected_amount = round(item.quantity * item.unit_price, 2)
                calc_line_sum += item.amount
                if abs(expected_amount - item.amount) > cls.TOLERANCE:
                    items_valid = False
                    errors.append(
                        f"Line item #{idx} ('{item.description}') calculation mismatch: "
                        f"qty ({item.quantity}) × unit price ({item.unit_price}) = {expected_amount:.2f}, "
                        f"but amount is {item.amount:.2f}"
                    )
        else:
            warnings.append("No individual line items detected in invoice.")

        if not items_valid:
            checks.line_items = "FAIL"

        # ----------------- Check D: Subtotal Validation -----------------
        if data.subtotal is not None and data.line_items:
            if abs(calc_line_sum - data.subtotal) > cls.TOLERANCE:
                checks.subtotal = "FAIL"
                errors.append(
                    f"Subtotal calculation mismatch: sum of line items ({calc_line_sum:.2f}) "
                    f"does not match extracted subtotal ({data.subtotal:.2f})"
                )
        elif data.subtotal is None and data.line_items:
            warnings.append(f"Subtotal not explicitly stated. Sum of line items is {calc_line_sum:.2f}.")

        # ----------------- Check E: Tax Validation -----------------
        if data.tax is not None and data.tax < 0:
            checks.tax = "FAIL"
            errors.append(f"Tax cannot be negative: {data.tax}")

        # ----------------- Check F: Total Validation -----------------
        if data.total is not None:
            if data.total <= 0:
                checks.total = "FAIL"
                errors.append(f"Invoice total must be strictly positive: {data.total}")
            
            # Check Subtotal + Tax = Total
            if data.subtotal is not None and data.tax is not None:
                expected_total = round(data.subtotal + data.tax, 2)
                if abs(expected_total - data.total) > cls.TOLERANCE:
                    checks.total = "FAIL"
                    checks.tax = "FAIL"
                    errors.append(
                        f"Total calculation mismatch: Subtotal ({data.subtotal:.2f}) + "
                        f"Tax ({data.tax:.2f}) = {expected_total:.2f}, but extracted Total is {data.total:.2f}"
                    )
            elif data.subtotal is not None and data.tax is None and len(data.line_items) > 0:
                # If total differs from subtotal without specified tax
                diff = round(data.total - data.subtotal, 2)
                if diff > cls.TOLERANCE:
                    warnings.append(f"Difference between Total and Subtotal is {diff:.2f}; assumed to be implied tax or shipping.")
        else:
            checks.total = "FAIL"
            errors.append("Total amount was not extracted.")

        # ----------------- Check H: Confidence / Status Assignment -----------------
        confidence = data.confidence if data.confidence is not None else 1.0
        if confidence < 0.75:
            warnings.append(f"Extraction confidence is low ({confidence * 100:.0f}%). Human review strongly advised.")

        # Determine overall status
        if any(val == "FAIL" for val in checks.model_dump().values()) or errors:
            status = "FLAGGED"
        elif warnings or confidence < 0.75:
            status = "REVIEW_REQUIRED"
        else:
            status = "VALID"

        return ValidationResultSchema(
            status=status,
            checks=checks,
            errors=errors,
            warnings=warnings,
            confidence=confidence
        )
