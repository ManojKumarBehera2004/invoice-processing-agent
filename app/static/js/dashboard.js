let allInvoices = [];
let currentFilter = 'ALL';

document.addEventListener('DOMContentLoaded', () => {
    loadDashboardStats();
    loadRecentAlerts();
    loadInvoices();
    // Poll stats & alerts every 15 seconds
    setInterval(loadDashboardStats, 15000);
    setInterval(loadRecentAlerts, 15000);
});

async function loadDashboardStats() {
    try {
        const res = await fetch('/api/dashboard/stats');
        if (!res.ok) return;
        const stats = await res.json();
        
        document.getElementById('stat-total').textContent = stats.total_invoices;
        document.getElementById('stat-valid').textContent = stats.valid_invoices;
        document.getElementById('stat-flagged').textContent = stats.flagged_invoices;
        document.getElementById('stat-review').textContent = stats.review_required_invoices;
        document.getElementById('stat-highval').textContent = stats.high_value_invoices;
    } catch (e) {
        console.error("Failed to load dashboard stats", e);
    }
}

async function loadRecentAlerts() {
    try {
        const res = await fetch('/api/dashboard/alerts');
        if (!res.ok) return;
        const alerts = await res.json();
        
        const container = document.getElementById('alerts-container');
        const badge = document.getElementById('alert-count-badge');
        badge.textContent = `${alerts.length} Alert${alerts.length === 1 ? '' : 's'}`;

        if (!alerts.length) {
            container.innerHTML = `
                <div style="color: var(--text-muted); text-align: center; padding: 20px;">
                    No system alerts recorded yet.
                </div>
            `;
            return;
        }

        container.innerHTML = alerts.map(a => {
            const isHighVal = a.alert_type === 'HIGH_VALUE';
            const icon = isHighVal ? 'fa-triangle-exclamation' : 'fa-circle-exclamation';
            const colorClass = isHighVal ? 'alert-warning' : 'alert-danger';
            const timeFormatted = new Date(a.timestamp).toLocaleTimeString();
            return `
                <div class="alert-box ${colorClass}" style="margin-bottom: 8px; padding: 10px 14px;">
                    <i class="fa-solid ${icon}" style="margin-top: 2px;"></i>
                    <div style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; font-weight: 600; font-size: 12px; margin-bottom: 2px;">
                            <span>${a.alert_type}: ${a.invoice_number || 'N/A'}</span>
                            <span style="opacity: 0.8;">${timeFormatted}</span>
                        </div>
                        <div style="font-size: 12px;">${a.message}</div>
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error("Failed to load alerts", e);
    }
}

async function loadInvoices() {
    try {
        const res = await fetch('/api/invoices');
        if (!res.ok) throw new Error("Failed to fetch invoices");
        allInvoices = await res.json();
        renderInvoicesTable();
    } catch (e) {
        console.error(e);
        document.getElementById('invoices-tbody').innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 30px; color: var(--danger);">
                    Failed to load invoices.
                </td>
            </tr>
        `;
    }
}

function setFilter(filter, el) {
    currentFilter = filter;
    document.querySelectorAll('#filter-pills .btn').forEach(btn => btn.classList.remove('active', 'btn-primary'));
    el.classList.add('active');
    renderInvoicesTable();
}

function filterInvoices() {
    renderInvoicesTable();
}

function renderInvoicesTable() {
    const query = document.getElementById('search-input').value.toLowerCase().trim();
    const tbody = document.getElementById('invoices-tbody');

    const filtered = allInvoices.filter(inv => {
        // Status filter
        if (currentFilter !== 'ALL' && inv.status !== currentFilter) {
            return false;
        }
        // Search filter
        if (query) {
            const num = (inv.invoice_number || '').toLowerCase();
            const vend = (inv.vendor_name || '').toLowerCase();
            if (!num.includes(query) && !vend.includes(query)) return false;
        }
        return true;
    });

    if (!filtered.length) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 40px; color: var(--text-muted);">
                    No invoices matching the current filter.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filtered.map(inv => {
        let badgeClass = 'badge-valid';
        if (inv.status === 'FLAGGED') badgeClass = 'badge-flagged';
        else if (inv.status === 'REVIEW_REQUIRED') badgeClass = 'badge-review';
        else if (inv.status === 'APPROVED') badgeClass = 'badge-approved';
        else if (inv.status === 'REJECTED') badgeClass = 'badge-rejected';

        const highValBadge = inv.high_value 
            ? `<span class="badge badge-highval"><i class="fa-solid fa-gem"></i> High Value</span>`
            : `<span style="color: var(--text-muted); font-size: 12px;">Standard</span>`;

        const totalFormatted = inv.total !== null 
            ? `₹${Number(inv.total).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            : '<span style="color: var(--danger);">Missing</span>';

        return `
            <tr>
                <td><strong>${inv.invoice_number || '<span style="color: var(--danger);">Unidentified</span>'}</strong></td>
                <td>${inv.vendor_name || '<span style="color: var(--text-muted);">Unknown Vendor</span>'}</td>
                <td>${inv.invoice_date || '<span style="color: var(--text-muted);">N/A</span>'}</td>
                <td><strong>${totalFormatted}</strong></td>
                <td><span class="badge ${badgeClass}">${inv.status}</span></td>
                <td>${highValBadge}</td>
                <td>
                    <div style="display: flex; gap: 8px;">
                        <a href="/invoices/${inv.id}" class="btn btn-sm btn-outline" title="View Detail">
                            <i class="fa-solid fa-eye"></i> View
                        </a>
                        <a href="/invoices/${inv.id}/review" class="btn btn-sm btn-primary" title="Review / Edit">
                            <i class="fa-solid fa-pen-to-square"></i> Review
                        </a>
                        <button class="btn btn-sm btn-outline" style="color: var(--danger);" onclick="deleteInvoice(${inv.id})" title="Delete">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

async function seedDemoCases() {
    const btn = document.getElementById('btn-seed-demo');
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Seeding Demo Invoices...`;

    try {
        const res = await fetch('/api/invoices/demo/seed', { method: 'POST' });
        if (!res.ok) throw new Error("Failed to seed sample invoices");
        showToast("Demo evaluation test cases populated successfully!", "success");
        await loadDashboardStats();
        await loadRecentAlerts();
        await loadInvoices();
    } catch (e) {
        showToast(e.message, "error");
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-database"></i> Load 4 Sample Evaluation Cases`;
    }
}

async function deleteInvoice(id) {
    if (!confirm("Are you sure you want to delete this invoice record?")) return;
    try {
        const res = await fetch(`/api/invoices/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error("Delete failed");
        showToast("Invoice deleted successfully", "success");
        allInvoices = allInvoices.filter(i => i.id !== id);
        renderInvoicesTable();
        loadDashboardStats();
    } catch (e) {
        showToast(e.message, "error");
    }
}
