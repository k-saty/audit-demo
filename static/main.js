document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("logForm");
    const result = document.getElementById("createResult");
    const fetchBtn = document.getElementById("fetchLogs");
    const queryTenant = document.getElementById("queryTenant");
    const logsTableBody = document.querySelector("#logsTable tbody");
    const logsCount = document.getElementById("logsCount");
    // Admin elements
    const retentionForm = document.getElementById("retentionForm");
    const retentionResult = document.getElementById("retentionResult");
    const auditTenant = document.getElementById("auditTenant");
    const fetchAuditsBtn = document.getElementById("fetchAudits");
    const auditsTableBody = document.querySelector("#auditsTable tbody");
    const auditsCount = document.getElementById("auditsCount");
    const runCleanupBtn = document.getElementById("runCleanup");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(form).entries());
        const resp = await fetch("/audit/log", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });
        if (resp.ok) {
            const json = await resp.json();
            result.textContent = `Created log ${json.log_id} @ ${json.timestamp}`;
            form.reset();
        } else {
            result.textContent = `Error: ${resp.status}`;
        }
    });

    fetchBtn.addEventListener("click", async () => {
        const tenant = queryTenant.value.trim();
        if (!tenant) return alert("Enter tenant id");
        const resp = await fetch(`/audit/logs?tenant_id=${encodeURIComponent(tenant)}`);
        if (!resp.ok) return alert(`Fetch failed: ${resp.status}`);
        const data = await resp.json();
        logsCount.textContent = `Count: ${data.count}`;
        logsTableBody.innerHTML = "";
        for (const l of data.logs) {
            const tr = document.createElement("tr");
            tr.innerHTML = `
        <td>${l.id}</td>
        <td>${l.timestamp}</td>
        <td>${l.agent_id}</td>
        <td>${l.session_id}</td>
        <td>${l.channel}</td>
        <td><pre>${escapeHtml(l.prompt)}</pre></td>
        <td><pre>${escapeHtml(l.response)}</pre></td>
      `;
            logsTableBody.appendChild(tr);
        }
    });

    // Retention form submit
    if (retentionForm) {
        retentionForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const data = Object.fromEntries(new FormData(retentionForm).entries());
            data.retention_days = Number(data.retention_days);
            const resp = await fetch('/admin/retention', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data),
            });
            if (resp.ok) {
                const j = await resp.json();
                retentionResult.textContent = `Retention saved for ${j.tenant_id}: ${j.retention_days} days`;
                retentionForm.reset();
            } else {
                retentionResult.textContent = `Error: ${resp.status}`;
            }
        });
    }

    // Fetch deletion audits
    if (fetchAuditsBtn) {
        fetchAuditsBtn.addEventListener('click', async () => {
            const tenant = (auditTenant && auditTenant.value.trim()) || '';
            const url = tenant ? `/admin/deletion-audits?tenant_id=${encodeURIComponent(tenant)}` : '/admin/deletion-audits';
            const resp = await fetch(url);
            if (!resp.ok) return alert(`Fetch audits failed: ${resp.status}`);
            const data = await resp.json();
            auditsCount.textContent = `Count: ${data.count}`;
            auditsTableBody.innerHTML = '';
            for (const a of data.audits) {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${a.id}</td>
                    <td>${a.tenant_id}</td>
                    <td>${a.retention_days}</td>
                    <td>${a.deleted_before}</td>
                    <td>${a.deleted_count}</td>
                    <td>${a.run_timestamp}</td>
                `;
                auditsTableBody.appendChild(tr);
            }
        });
    }

    // Run cleanup (demo only)
    if (runCleanupBtn) {
        runCleanupBtn.addEventListener('click', async () => {
            runCleanupBtn.disabled = true;
            runCleanupBtn.textContent = 'Running...';
            try {
                const resp = await fetch('/admin/run-cleanup', { method: 'POST' });
                if (!resp.ok) return alert(`Cleanup failed: ${resp.status}`);
                const data = await resp.json();
                alert(`Cleanup completed, audits created: ${data.count}`);
            } finally {
                runCleanupBtn.disabled = false;
                runCleanupBtn.textContent = 'Run cleanup (demo only)';
            }
        });
    }

    function escapeHtml(s) {
        return String(s)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }
});
