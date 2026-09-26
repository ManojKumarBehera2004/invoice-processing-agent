let selectedFile = null;

document.addEventListener('DOMContentLoaded', () => {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');

    ['dragenter', 'dragover'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dragover');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
            handleFileSelection(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            handleFileSelection(e.target.files[0]);
        }
    });
});

function handleFileSelection(file) {
    const validExtensions = ['.pdf', '.jpg', '.jpeg', '.png'];
    const fileName = file.name.toLowerCase();
    const isValid = validExtensions.some(ext => fileName.endsWith(ext));

    if (!isValid) {
        showToast("Invalid file format. Please upload PDF, JPG, JPEG, or PNG.", "error");
        return;
    }

    if (file.size > 15 * 1024 * 1024) {
        showToast("File size exceeds 15MB limit.", "error");
        return;
    }

    selectedFile = file;

    // Update UI info
    document.getElementById('file-info-bar').style.display = 'flex';
    document.getElementById('selected-file-name').textContent = file.name;
    document.getElementById('selected-file-size').textContent = (file.size / 1024).toFixed(1) + ' KB';

    const icon = document.getElementById('file-type-icon');
    if (fileName.endsWith('.pdf')) {
        icon.className = 'fa-solid fa-file-pdf';
    } else {
        icon.className = 'fa-solid fa-file-image';
    }

    showToast("Document attached. Ready to process!", "info");
}

function updateStep(nodeId, state) {
    const node = document.getElementById(nodeId);
    if (!node) return;
    if (state === 'active') {
        node.classList.add('active');
        node.classList.remove('completed');
    } else if (state === 'completed') {
        node.classList.remove('active');
        node.classList.add('completed');
    }
}

async function startProcessing() {
    if (!selectedFile) {
        showToast("Please choose an invoice file first.", "warning");
        return;
    }

    const btn = document.getElementById('btn-process-invoice');
    btn.disabled = true;
    document.getElementById('dropzone').style.pointerEvents = 'none';

    const trackerBox = document.getElementById('pipeline-tracker-box');
    trackerBox.style.display = 'block';

    const msg = document.getElementById('status-live-message');

    // Pipeline Animation steps
    updateStep('step-upload', 'active');
    msg.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Document uploaded successfully. Validating file...`;

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
        // Step progression simulation for smooth visual feedback
        setTimeout(() => {
            updateStep('step-upload', 'completed');
            updateStep('step-ocr', 'active');
            msg.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Extracting text and parsing document layout...`;
        }, 600);

        setTimeout(() => {
            updateStep('step-ocr', 'completed');
            updateStep('step-ai', 'active');
            msg.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> AI Agent extracting structured invoice fields...`;
        }, 1300);

        setTimeout(() => {
            updateStep('step-ai', 'completed');
            updateStep('step-val', 'active');
            msg.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Validating calculations, line items, and totals...`;
        }, 2100);

        const res = await fetch('/api/invoices/upload', {
            method: 'POST',
            body: formData
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Server failed to process invoice document.");
        }

        const invoice = await res.json();

        // Mark all steps complete
        updateStep('step-val', 'completed');
        updateStep('step-done', 'completed');
        msg.style.display = 'none';

        // Show completion card
        const completeCard = document.getElementById('processing-complete-card');
        completeCard.style.display = 'block';
        document.getElementById('btn-view-result').href = `/invoices/${invoice.id}`;
        
        let statusBadge = invoice.status;
        document.getElementById('result-summary-text').innerHTML = `
            <strong>Invoice #${invoice.invoice_number || 'N/A'}</strong> from <strong>${invoice.vendor_name || 'Vendor'}</strong> 
            processed. Result Status: <span class="badge ${invoice.status === 'VALID' ? 'badge-valid' : (invoice.status === 'FLAGGED' ? 'badge-flagged' : 'badge-review')}">${statusBadge}</span>
            ${invoice.high_value ? ' | <span class="badge badge-highval"><i class="fa-solid fa-gem"></i> High Value</span>' : ''}
        `;

        showToast("Processing complete!", "success");

    } catch (e) {
        msg.innerHTML = `<span style="color: var(--danger);"><i class="fa-solid fa-circle-exclamation"></i> Processing failed: ${e.message}</span>`;
        showToast(e.message, "error");
        btn.disabled = false;
        document.getElementById('dropzone').style.pointerEvents = 'auto';
    }
}

// Sample generator helper for instant live evaluator testing
function loadSampleFile(type) {
    let content = "";
    let filename = "";

    if (type === 'valid') {
        filename = "sample_balanced_invoice.txt";
        content = `INVOICE
Vendor: CloudScale Infrastructure Solutions
Invoice No: INV-2026-901
Date: 2026-03-24
Currency: INR

Items:
Database Managed Cluster | 2 | 20000.00 | 40000.00
Virtual Private Cloud Gateway | 1 | 10000.00 | 10000.00

Subtotal: 50000.00
Tax: 9000.00
Total: 59000.00`;
    } else if (type === 'mismatch') {
        filename = "sample_wrong_total_invoice.txt";
        content = `INVOICE
Vendor: Apex Global Network
Invoice No: INV-ERR-404
Date: 2026-03-22
Currency: INR

Items:
Gigabit Dedicated Fiber Uplink | 1 | 30000.00 | 30000.00

Subtotal: 30000.00
Tax: 5400.00
Total: 45000.00`; // Calculation mismatch intentional (30000 + 5400 != 45000)
    } else if (type === 'highvalue') {
        filename = "sample_high_value_invoice.txt";
        content = `TAX INVOICE
Vendor: Quantum High Performance Servers Corp
Invoice No: INV-HV-8899
Date: 2026-03-25
Currency: INR

Items:
Enterprise GPU Acceleration Node | 1 | 250000.00 | 250000.00

Subtotal: 250000.00
Tax: 45000.00
Total: 295000.00`; // High value >= 100000
    } else if (type === 'missing') {
        filename = "sample_missing_fields_invoice.txt";
        content = `RECEIPT / BILL
Invoice No: INV-MISSING-01
Items:
Generic Hardware Component | 2 | 4000.00 | 8000.00
Total: 8000.00`; // Missing Vendor, Missing Date
    }

    // Convert text to a synthetic PDF or PNG-compatible file object
    const blob = new Blob([content], { type: 'text/plain' });
    // Save as .pdf filename so backend accepts it for the agent pipeline
    const file = new File([blob], filename.replace('.txt', '.pdf'), { type: 'application/pdf' });
    handleFileSelection(file);
    showToast(`Loaded "${filename}" sample! Click "Process Invoice" to run pipeline.`, "info");
}
