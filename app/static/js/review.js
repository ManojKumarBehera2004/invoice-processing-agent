function recalcRow(inputEl) {
    const row = inputEl.closest('tr');
    const qty = parseFloat(row.querySelector('.item-qty').value) || 0;
    const price = parseFloat(row.querySelector('.item-price').value) || 0;
    const amountInput = row.querySelector('.item-amount');
    amountInput.value = (qty * price).toFixed(2);
    updateFinancials();
}

function updateFinancials() {
    // Optionally update subtotal if user wants auto sum
}

function autoCalculateTotals() {
    let sum = 0;
    document.querySelectorAll('.item-row').forEach(row => {
        const amt = parseFloat(row.querySelector('.item-amount').value) || 0;
        sum += amt;
    });

    document.getElementById('edit-subtotal').value = sum.toFixed(2);
    
    const taxInput = document.getElementById('edit-tax');
    let taxVal = parseFloat(taxInput.value) || 0;
    if (taxVal === 0) {
        // Standard 18% GST estimate if left empty
        taxVal = sum * 0.18;
        taxInput.value = taxVal.toFixed(2);
    }

    const totalInput = document.getElementById('edit-total');
    totalInput.value = (sum + taxVal).toFixed(2);

    showToast("Subtotal and Grand Total balanced to match line items!", "info");
}

function addLineItemRow() {
    const tbody = document.getElementById('line-items-tbody');
    const tr = document.createElement('tr');
    tr.className = 'item-row';
    tr.innerHTML = `
        <td>
            <input type="text" class="form-control item-desc" placeholder="New Item description" style="padding: 6px 10px; font-size: 13px;">
        </td>
        <td>
            <input type="number" step="any" class="form-control item-qty" value="1" style="text-align: right; padding: 6px 10px; font-size: 13px;" oninput="recalcRow(this)">
        </td>
        <td>
            <input type="number" step="any" class="form-control item-price" value="0.00" style="text-align: right; padding: 6px 10px; font-size: 13px;" oninput="recalcRow(this)">
        </td>
        <td>
            <input type="number" step="any" class="form-control item-amount" value="0.00" style="text-align: right; padding: 6px 10px; font-size: 13px; font-weight: 600;" oninput="updateFinancials()">
        </td>
        <td>
            <button type="button" class="btn btn-sm" style="color: var(--danger); padding: 4px;" onclick="removeLineItemRow(this)" title="Delete Item">
                <i class="fa-solid fa-trash"></i>
            </button>
        </td>
    `;
    tbody.appendChild(tr);
}

function removeLineItemRow(btn) {
    btn.closest('tr').remove();
    updateFinancials();
}

function collectPayload() {
    const lineItems = [];
    document.querySelectorAll('.item-row').forEach(row => {
        const desc = row.querySelector('.item-desc').value.trim();
        const qty = parseFloat(row.querySelector('.item-qty').value) || 0;
        const price = parseFloat(row.querySelector('.item-price').value) || 0;
        const amt = parseFloat(row.querySelector('.item-amount').value) || 0;
        if (desc) {
            lineItems.push({
                description: desc,
                quantity: qty,
                unit_price: price,
                amount: amt
            });
        }
    });

    const subtotalVal = document.getElementById('edit-subtotal').value;
    const taxVal = document.getElementById('edit-tax').value;
    const totalVal = document.getElementById('edit-total').value;

    return {
        vendor_name: document.getElementById('edit-vendor').value.trim() || null,
        invoice_number: document.getElementById('edit-inv-number').value.trim() || null,
        invoice_date: document.getElementById('edit-date').value.trim() || null,
        currency: document.getElementById('edit-currency').value.trim() || "INR",
        subtotal: subtotalVal !== "" ? parseFloat(subtotalVal) : null,
        tax: taxVal !== "" ? parseFloat(taxVal) : null,
        total: totalVal !== "" ? parseFloat(totalVal) : null,
        line_items: lineItems
    };
}

async function saveAndRevalidate(id) {
    const payload = collectPayload();
    try {
        const res = await fetch(`/api/invoices/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to save invoice updates.");
        }

        const invoice = await res.json();
        showToast("Invoice updated and re-validated!", "success");

        // Update header badge
        const badge = document.getElementById('header-status-badge');
        badge.textContent = invoice.status;
        badge.className = `badge ${invoice.status === 'VALID' ? 'badge-valid' : (invoice.status === 'FLAGGED' ? 'badge-flagged' : (invoice.status === 'APPROVED' ? 'badge-approved' : 'badge-review'))}`;

        // Parse validation errors
        let valResult = { checks: {}, errors: [], warnings: [] };
        if (invoice.validation_errors) {
            try { valResult = JSON.parse(invoice.validation_errors); } catch(e){}
        }

        updateCheckUI('chk-required', 'badge-chk-required', valResult.checks.required_fields);
        updateCheckUI('chk-items', 'badge-chk-items', valResult.checks.line_items);
        updateCheckUI('chk-subtotal', 'badge-chk-subtotal', valResult.checks.subtotal);
        updateCheckUI('chk-tax', 'badge-chk-tax', valResult.checks.tax);
        updateCheckUI('chk-total', 'badge-chk-total', valResult.checks.total);
        updateCheckUI('chk-date', 'badge-chk-date', valResult.checks.date);

        // Update error list
        const errContainer = document.getElementById('live-errors-container');
        if (valResult.errors && valResult.errors.length) {
            errContainer.innerHTML = `
                <div class="form-label" style="color: var(--danger);"><i class="fa-solid fa-triangle-exclamation"></i> Discrepancies:</div>
                ${valResult.errors.map(e => `<div class="alert-box alert-danger" style="margin-bottom: 8px; padding: 10px 12px;"><span>${e}</span></div>`).join('')}
            `;
        } else {
            errContainer.innerHTML = `
                <div class="alert-box" style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); color: #34d399; padding: 10px 12px;">
                    <i class="fa-solid fa-circle-check"></i>
                    <span>All calculations and fields are verified and balanced!</span>
                </div>
            `;
        }

    } catch (e) {
        showToast(e.message, "error");
    }
}

function updateCheckUI(cardId, badgeId, statusVal) {
    const card = document.getElementById(cardId);
    const badge = document.getElementById(badgeId);
    if (!card || !badge) return;

    const isPass = statusVal === 'PASS';
    badge.textContent = statusVal || 'N/A';
    badge.className = `badge ${isPass ? 'badge-valid' : 'badge-flagged'}`;

    if (isPass) {
        card.classList.add('pass');
        card.classList.remove('fail');
        card.querySelector('.check-icon').className = 'fa-solid fa-circle-check text-success check-icon';
    } else {
        card.classList.add('fail');
        card.classList.remove('pass');
        card.querySelector('.check-icon').className = 'fa-solid fa-circle-xmark text-danger check-icon';
    }
}

async function approveCurrentInvoice(id) {
    try {
        const res = await fetch(`/api/invoices/${id}/approve`, { method: 'POST' });
        if (!res.ok) throw new Error("Approval failed");
        showToast("Invoice marked as APPROVED!", "success");
        const badge = document.getElementById('header-status-badge');
        badge.textContent = "APPROVED";
        badge.className = "badge badge-approved";
    } catch (e) {
        showToast(e.message, "error");
    }
}

async function rejectCurrentInvoice(id) {
    try {
        const res = await fetch(`/api/invoices/${id}/reject`, { method: 'POST' });
        if (!res.ok) throw new Error("Rejection failed");
        showToast("Invoice marked as REJECTED.", "info");
        const badge = document.getElementById('header-status-badge');
        badge.textContent = "REJECTED";
        badge.className = "badge badge-rejected";
    } catch (e) {
        showToast(e.message, "error");
    }
}
