console.log("main.js loaded!");

// ============ GLOBAL STATE ============
let currentUser = null;
let authToken = null;

// ============ AUTH HELPERS ============
function getAuthHeaders() {
    const headers = { "Content-Type": "application/json" };
    if (currentUser) {
        headers["X-User"] = currentUser.username;
    }
    return headers;
}

async function apiCall(endpoint, method = "GET", body = null) {
    const opts = {
        method: method,
        headers: getAuthHeaders(),
    };
    if (body) {
        opts.body = JSON.stringify(body);
    }
    return fetch(endpoint, opts);
}

async function initializeAuth() {
    try {
        // Query server for current session user
        const resp = await fetch('/auth/me', { method: 'GET', headers: { 'Content-Type': 'application/json' } });
        if (resp.ok) {
            currentUser = await resp.json();
        } else {
            currentUser = null;
        }
    } catch (err) {
        console.error('Auth init error:', err);
        currentUser = null;
    }

    updateUIForUser(currentUser);
}

function updateUIForUser(user) {
    const landingPage = document.getElementById("landingPage");
    const dashboardPage = document.getElementById("dashboardPage");
    const nameEl = document.getElementById("currentUserName");
    const roleEl = document.getElementById("currentUserRole");
    const adminNavItem = document.getElementById("adminNavItem");
    const adminPanel = document.getElementById("admin-panel");
    const adminTabs = document.querySelectorAll('.admin-tab');
    const loginBtn = document.getElementById("loginBtn");
    const logoutBtn = document.getElementById("logoutBtn");

    if (!user) {
        // Show landing page, hide dashboard
        if (landingPage) landingPage.style.display = 'flex';
        if (dashboardPage) dashboardPage.style.display = 'none';

        nameEl.textContent = 'Not signed in';
        roleEl.textContent = '';
        roleEl.className = 'user-role';
        if (adminNavItem) adminNavItem.style.display = 'none';
        if (adminPanel) adminPanel.style.display = 'none';
        adminTabs.forEach(tab => tab.style.display = 'none');
        const adminOnlyEls = document.querySelectorAll('.admin-only');
        adminOnlyEls.forEach(el => el.style.display = 'none');
        if (loginBtn) loginBtn.style.display = '';
        if (logoutBtn) logoutBtn.style.display = 'none';
        return;
    }

    // Show dashboard, hide landing page
    if (landingPage) landingPage.style.display = 'none';
    if (dashboardPage) dashboardPage.style.display = 'flex';

    nameEl.textContent = user.username;
    roleEl.textContent = `(${user.role})`;
    roleEl.className = `user-role role-${user.role}`;

    if (user.role === 'admin') {
        if (adminNavItem) adminNavItem.style.display = 'block';
        // Don't force display on adminPanel - let CSS class handle visibility
        adminTabs.forEach(tab => tab.style.display = 'flex');
        const adminOnlyEls = document.querySelectorAll('.admin-only');
        adminOnlyEls.forEach(el => el.style.display = '');
    } else {
        if (adminNavItem) adminNavItem.style.display = 'none';
        // Remove admin panel from view by ensuring it's not active
        if (adminPanel) adminPanel.classList.remove('active');
        adminTabs.forEach(tab => tab.style.display = 'none');
        const adminOnlyEls = document.querySelectorAll('.admin-only');
        adminOnlyEls.forEach(el => el.style.display = 'none');
    }

    if (loginBtn) loginBtn.style.display = 'none';
    if (logoutBtn) logoutBtn.style.display = '';
}

document.addEventListener("DOMContentLoaded", async () => {
    console.log("DOMContentLoaded fired");

    // Try to load current user
    await initializeAuth();

    // ============ NAVIGATION ============
    const navItems = document.querySelectorAll(".nav-item");
    const contentSections = document.querySelectorAll(".content-section");

    navItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const sectionId = item.dataset.section;

            // Update active nav item
            navItems.forEach(nav => nav.classList.remove("active"));
            item.classList.add("active");

            // Update visible section
            contentSections.forEach(section => section.classList.remove("active"));
            const section = document.getElementById(sectionId);
            if (section) {
                section.classList.add("active");
            }
        });
    });

    // Refresh button
    const refreshBtn = document.getElementById("refreshBtn");
    if (refreshBtn) {
        refreshBtn.addEventListener("click", () => {
            location.reload();
        });
    }

    // ============ ADMIN PANEL & USER CREATION ============
    const createUserForm = document.getElementById("createUserForm");
    const createUserResult = document.getElementById("createUserResult");
    const fetchUsersBtn = document.getElementById("fetchUsersBtn");
    const usersTableBody = document.querySelector("#usersTable tbody");
    const usersCount = document.getElementById("usersCount");

    if (createUserForm) {
        createUserForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const username = document.getElementById("newUsername").value;
            const role = document.getElementById("newUserRole").value;

            try {
                const resp = await apiCall("/users/create", "POST", {
                    username: username,
                    role: role,
                });
                if (resp.ok) {
                    createUserResult.classList.add("show", "success");
                    createUserResult.innerHTML = `✓ User '${username}' created as ${role}`;
                    createUserForm.reset();
                    setTimeout(() => fetchUsersBtn.click(), 1000);
                } else {
                    const err = await resp.json();
                    createUserResult.classList.add("show", "error");
                    createUserResult.innerHTML = `✗ Error: ${err.detail || resp.status}`;
                }
            } catch (err) {
                createUserResult.classList.add("show", "error");
                createUserResult.innerHTML = `✗ Error: ${err.message}`;
            }
        });
    }

    if (fetchUsersBtn) {
        fetchUsersBtn.addEventListener("click", async () => {
            try {
                const resp = await apiCall("/users", "GET");
                if (!resp.ok) {
                    alert(`Fetch failed: ${resp.status}`);
                    return;
                }
                const users = await resp.json();
                usersCount.textContent = `Total Users: ${users.length}`;
                usersTableBody.innerHTML = "";
                for (const user of users) {
                    const tr = document.createElement("tr");
                    const promoteBtn = user.role === "viewer"
                        ? `<button class="btn btn-small" onclick="promoteUser('${user.username}')">Promote to Admin</button>`
                        : `<span style="color: #0066cc; font-weight: bold;">Admin</span>`;
                    tr.innerHTML = `
                        <td>${user.username}</td>
                        <td><span class="role-badge ${user.role}">${user.role}</span></td>
                        <td>${new Date(user.created_at).toLocaleDateString()}</td>
                        <td>${promoteBtn}</td>
                    `;
                    usersTableBody.appendChild(tr);
                }
            } catch (err) {
                alert(`Error: ${err.message}`);
            }
        });
    }

    window.promoteUser = async (username) => {
        if (!confirm(`Promote ${username} to admin?`)) return;
        try {
            const resp = await apiCall(`/users/${username}/promote`, "POST", {});
            if (resp.ok) {
                alert("User promoted to admin");
                fetchUsersBtn.click();
            } else {
                const err = await resp.json();
                alert(`Error: ${err.detail || resp.status}`);
            }
        } catch (err) {
            alert(`Error: ${err.message}`);
        }
    };

    // ============ AUTH UI HANDLERS ============
    const loginBtn = document.getElementById('loginBtn');
    const logoutBtn = document.getElementById('logoutBtn');
    const loginModal = document.getElementById('loginModal');
    const loginForm = document.getElementById('loginForm');
    const cancelLogin = document.getElementById('cancelLogin');
    const loginResult = document.getElementById('loginResult');
    const landingSignInBtn = document.getElementById('landingSignInBtn');

    console.log('[DEBUG] Auth elements:', {
        loginBtn: !!loginBtn,
        logoutBtn: !!logoutBtn,
        loginModal: !!loginModal,
        loginForm: !!loginForm,
        cancelLogin: !!cancelLogin,
        loginResult: !!loginResult,
        landingSignInBtn: !!landingSignInBtn
    });

    // Landing page sign in button
    if (landingSignInBtn) {
        landingSignInBtn.addEventListener('click', () => {
            console.log('[DEBUG] Landing Sign In button clicked');
            if (loginModal) {
                loginModal.style.display = 'flex';
                loginModal.classList.add('show');
                console.log('[DEBUG] Modal should now be visible');
            }
        });
    }

    if (loginBtn) {
        loginBtn.addEventListener('click', () => {
            console.log('[DEBUG] Header Sign In button clicked');
            if (loginModal) {
                loginModal.style.display = 'flex';
                loginModal.classList.add('show');
                console.log('[DEBUG] Modal should now be visible');
            }
        });
    }

    if (cancelLogin) {
        cancelLogin.addEventListener('click', () => {
            if (loginModal) {
                loginModal.style.display = 'none';
                loginModal.classList.remove('show');
            }
            if (loginResult) loginResult.innerHTML = '';
        });
    }

    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            console.log('[DEBUG] Login form submitted');
            e.preventDefault();
            const username = document.getElementById('loginUsername').value.trim();
            const role = document.getElementById('loginRole').value;
            console.log('[DEBUG] Login attempt:', { username, role });
            if (!username) return alert('Enter username');

            try {
                const resp = await fetch('/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: username, role: role })
                });
                console.log('[DEBUG] Login response status:', resp.status);
                if (!resp.ok) {
                    const err = await resp.json().catch(() => ({}));
                    console.error('[DEBUG] Login error:', err);
                    if (loginResult) loginResult.innerHTML = `✗ ${err.detail || resp.statusText}`;
                    return;
                }
                const user = await resp.json();
                console.log('[DEBUG] Login successful:', user);
                currentUser = user;
                updateUIForUser(currentUser);
                if (loginModal) {
                    loginModal.style.display = 'none';
                    loginModal.classList.remove('show');
                }
                if (loginResult) loginResult.innerHTML = '';
            } catch (err) {
                console.error('[DEBUG] Login error', err);
                if (loginResult) loginResult.innerHTML = `✗ ${err.message}`;
            }
        });
    }

    if (logoutBtn) {
        logoutBtn.addEventListener('click', async () => {
            try {
                const resp = await fetch('/auth/logout', { method: 'POST' });
                currentUser = null;
                updateUIForUser(null);
            } catch (err) {
                console.error('Logout error', err);
            }
        });
    }

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

    // PII elements
    const fetchPiiSummaryBtn = document.getElementById("fetchPiiSummary");
    const piiTenant = document.getElementById("piiTenant");
    const piiSummaryResult = document.getElementById("piiSummaryResult");
    const fetchPiiLogsBtn = document.getElementById("fetchPiiLogs");
    const piiLogsFilter = document.getElementById("piiLogsFilter");
    const piiRiskFilter = document.getElementById("piiRiskFilter");
    const piiLogsTableBody = document.querySelector("#piiLogsTable tbody");
    const piiLogsCount = document.getElementById("piiLogsCount");
    const piiDetailsCard = document.getElementById("piiDetailsCard");
    const closePiiDetailsBtn = document.getElementById("closePiiDetails");

    // Compliance export elements
    const complianceExportForm = document.getElementById("complianceExportForm");
    const complianceExportResult = document.getElementById("complianceExportResult");
    const complianceTenantId = document.getElementById("complianceTenantId");

    console.log("complianceExportForm:", complianceExportForm);
    console.log("complianceExportResult:", complianceExportResult);
    console.log("complianceTenantId:", complianceTenantId);

    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const data = Object.fromEntries(new FormData(form).entries());
            const resp = await fetch("/audit/log", {
                method: "POST",
                headers: { "Content-Type": "application/json", ...getAuthHeaders() },
                body: JSON.stringify(data),
            });
            if (resp.ok) {
                const json = await resp.json();
                result.classList.add("show", "success");
                result.innerHTML = `✓ Created log ${json.log_id} @ ${json.timestamp}`;
                form.reset();
            } else {
                result.classList.add("show", "error");
                result.innerHTML = `✗ Error: ${resp.status}`;
            }
        });
    }

    fetchBtn.addEventListener("click", async () => {
        const tenant = queryTenant.value.trim();
        if (!tenant) return alert("Enter tenant id");
        const resp = await fetch(`/audit/logs?tenant_id=${encodeURIComponent(tenant)}`, {
            headers: getAuthHeaders(),
        });
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

    if (retentionForm) {
        retentionForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const data = Object.fromEntries(new FormData(retentionForm).entries());
            data.retention_days = Number(data.retention_days);
            const resp = await apiCall('/admin/retention', 'POST', data);
            if (resp.ok) {
                const j = await resp.json();
                retentionResult.classList.add("show", "success");
                retentionResult.innerHTML = `✓ Retention saved for ${j.tenant_id}: ${j.retention_days} days`;
                retentionForm.reset();
            } else {
                retentionResult.classList.add("show", "error");
                const err = await resp.json().catch(() => ({}));
                retentionResult.innerHTML = `✗ Error: ${err.detail || resp.status}`;
            }
        });
    }

    // Fetch deletion audits
    if (fetchAuditsBtn) {
        fetchAuditsBtn.addEventListener('click', async () => {
            const tenant = (auditTenant && auditTenant.value.trim()) || '';
            const url = tenant ? `/admin/deletion-audits?tenant_id=${encodeURIComponent(tenant)}` : '/admin/deletion-audits';
            const resp = await apiCall(url, 'GET');
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({}));
                alert(`Fetch audits failed: ${err.detail || resp.status}`);
                return;
            }
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
                const resp = await apiCall('/admin/run-cleanup', 'POST', {});
                if (!resp.ok) {
                    const err = await resp.json().catch(() => ({}));
                    alert(`Cleanup failed: ${err.detail || resp.status}`);
                    return;
                }
                const data = await resp.json();
                alert(`Cleanup completed, audits created: ${data.count}`);
            } finally {
                runCleanupBtn.disabled = false;
                runCleanupBtn.textContent = 'Run cleanup (demo only)';
            }
        });
    }

    // ============ PII DETECTION UI ============

    // View PII Summary
    if (fetchPiiSummaryBtn) {
        fetchPiiSummaryBtn.addEventListener('click', async () => {
            const tenant = piiTenant.value.trim();
            if (!tenant) return alert("Enter tenant ID");

            const resp = await apiCall(`/pii/summary?tenant_id=${encodeURIComponent(tenant)}`, 'GET');
            if (!resp.ok) return alert(`Failed to fetch PII summary: ${resp.status}`);

            const data = await resp.json();
            let html = `
                <div class="pii-summary">
                    <div class="pii-stat">
                        <div class="pii-stat-value">${data.total_pii_detections}</div>
                        <div class="pii-stat-label">Total Detections</div>
                    </div>
                    <div class="pii-stat">
                        <div class="pii-stat-value" style="color: #d63a2b;">${data.high_risk_count}</div>
                        <div class="pii-stat-label">High Risk Items</div>
                    </div>
                </div>
            `;

            if (Object.keys(data.pii_type_breakdown).length > 0) {
                html += '<h4>PII Types Detected:</h4><ul>';
                for (const [type, count] of Object.entries(data.pii_type_breakdown)) {
                    html += `<li><strong>${type}:</strong> ${count} occurrences</li>`;
                }
                html += '</ul>';
            }

            if (data.recent_detections.length > 0) {
                html += '<h4>Recent Detections:</h4><ul>';
                for (const det of data.recent_detections) {
                    const badge = det.high_risk ? '<span class="pii-badge high">HIGH RISK</span>' : '';
                    const types = det.pii_types.join(', ');
                    html += `<li>${det.timestamp} - ${det.pii_count} items (${types}) ${badge}</li>`;
                }
                html += '</ul>';
            }

            piiSummaryResult.innerHTML = html;
        });
    }

    // Fetch PII Logs with filtering
    if (fetchPiiLogsBtn) {
        fetchPiiLogsBtn.addEventListener('click', async () => {
            const tenant = piiLogsFilter.value.trim();
            const riskLevel = piiRiskFilter.value;

            let url = '/pii/logs';
            const params = new URLSearchParams();
            if (tenant) params.append('tenant_id', tenant);
            if (riskLevel) params.append('risk_level', riskLevel);
            if (params.toString()) url += '?' + params.toString();

            const resp = await apiCall(url, 'GET');
            if (!resp.ok) return alert(`Failed to fetch PII logs: ${resp.status}`);

            const data = await resp.json();
            piiLogsCount.textContent = `Found: ${data.count}`;
            piiLogsTableBody.innerHTML = '';

            for (const log of data.logs) {
                const tr = document.createElement('tr');
                const highRiskBadge = log.high_risk ? '<span class="pii-badge high">HIGH</span>' : '<span class="pii-badge low">LOW</span>';
                const typesList = log.pii_types.join(', ');
                tr.innerHTML = `
                    <td>${log.detection_id.substring(0, 8)}...</td>
                    <td>${log.timestamp}</td>
                    <td>${log.pii_count}</td>
                    <td>${highRiskBadge}</td>
                    <td>${typesList}</td>
                    <td><button onclick="viewPiiDetails('${log.detection_id}')">View</button></td>
                `;
                piiLogsTableBody.appendChild(tr);
            }
        });
    }

    // View PII Details
    window.viewPiiDetails = async (detectionId) => {
        const resp = await apiCall(`/pii/details/${detectionId}`, 'GET');
        if (!resp.ok) return alert(`Failed to fetch details: ${resp.status}`);

        const data = await resp.json();
        let html = `<h4>Detection Details</h4>`;
        html += `<p><strong>Audit Log ID:</strong> ${data.audit_log_id}</p>`;
        html += `<p><strong>Timestamp:</strong> ${data.detection_timestamp}</p>`;
        html += `<p><strong>Total PII Found:</strong> <strong style="color: #ff4444;">${data.pii_count}</strong></p>`;
        html += `<p><strong>Fields Scanned:</strong> ${data.fields_scanned.join(', ')}</p>`;

        // Show original audit log (prompt and response)
        if (data.audit_log) {
            html += `<div class="card" style="margin-top: 15px; background-color: #f8f9fb;">`;
            html += `<h5 style="margin: 0 0 12px 0; color: #001a4d;">📋 Original Conversation</h5>`;
            html += `<p style="font-size: 13px; color: #666d7a; margin-bottom: 12px;"><strong>Agent:</strong> ${data.audit_log.agent_id} | <strong>Session:</strong> ${data.audit_log.session_id} | <strong>Channel:</strong> ${data.audit_log.channel}</p>`;

            html += `<div style="margin-bottom: 16px;">`;
            html += `<strong style="display: block; margin-bottom: 8px; font-size: 13px; color: #0066cc;">📨 Prompt</strong>`;
            html += `<div style="background-color: #fff; border-radius: 6px; border-left: 4px solid #0066cc; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">`;
            html += `<pre style="margin: 0; padding: 12px; font-size: 13px; line-height: 1.5; max-height: 250px; overflow-y: auto; white-space: pre-wrap; word-break: break-word; color: #1a2332;">${escapeHtml(data.audit_log.prompt)}</pre>`;
            html += `</div>`;
            html += `</div>`;

            html += `<div>`;
            html += `<strong style="display: block; margin-bottom: 8px; font-size: 13px; color: #28a745;">💬 Response</strong>`;
            html += `<div style="background-color: #fff; border-radius: 6px; border-left: 4px solid #28a745; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">`;
            html += `<pre style="margin: 0; padding: 12px; font-size: 13px; line-height: 1.5; max-height: 250px; overflow-y: auto; white-space: pre-wrap; word-break: break-word; color: #1a2332;">${escapeHtml(data.audit_log.response)}</pre>`;
            html += `</div>`;
            html += `</div>`;
            html += `</div>`;
        }

        // Show NER API Response
        if (data.ner_response_prompt || data.ner_response_response) {
            html += `<div class="card" style="margin-top: 16px; background-color: #f8f9fb; border: 2px solid #0066cc;">`;
            html += `<h5 style="margin: 0 0 12px 0; color: #001a4d;">🤖 Hugging Face NER API Response</h5>`;

            if (data.ner_response_prompt) {
                html += `<div style="margin-bottom: 16px;">`;
                html += `<strong style="display: block; margin-bottom: 8px; font-size: 13px; color: #0066cc;">Prompt NER Results</strong>`;
                html += `<div style="background-color: #fff; border-radius: 6px; border-left: 4px solid #0066cc; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">`;
                html += `<pre style="margin: 0; padding: 12px; font-size: 12px; line-height: 1.4; max-height: 280px; overflow-y: auto; white-space: pre-wrap; word-break: break-word; color: #1a2332;">${escapeHtml(JSON.stringify(data.ner_response_prompt, null, 2))}</pre>`;
                html += `</div>`;
                html += `</div>`;
            }

            if (data.ner_response_response) {
                html += `<div>`;
                html += `<strong style="display: block; margin-bottom: 8px; font-size: 13px; color: #28a745;">Response NER Results</strong>`;
                html += `<div style="background-color: #fff; border-radius: 6px; border-left: 4px solid #28a745; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">`;
                html += `<pre style="margin: 0; padding: 12px; font-size: 12px; line-height: 1.4; max-height: 280px; overflow-y: auto; white-space: pre-wrap; word-break: break-word; color: #1a2332;">${escapeHtml(JSON.stringify(data.ner_response_response, null, 2))}</pre>`;
                html += `</div>`;
                html += `</div>`;
            }

            html += `</div>`;
        }

        if (data.high_risk_items.length > 0) {
            html += `<h5 style="margin-top: 20px;">🚨 High Risk Items:</h5>`;
            for (const item of data.high_risk_items) {
                html += `
                    <div class="pii-item high">
                        <strong>Type:</strong> ${item.type}<br>
                        <strong>Field:</strong> ${item.field}<br>
                        <strong>Value:</strong> <code>${escapeHtml(item.value)}</code>
                    </div>
                `;
            }
        }

        if (data.details.length > 0) {
            html += `<h5>All Detected Items:</h5>`;
            for (const item of data.details) {
                const riskClass = item.risk_level || 'low';
                html += `
                    <div class="pii-item ${riskClass}">
                        <span class="pii-badge ${riskClass}">${item.risk_level.toUpperCase()}</span>
                        <strong>${item.type}</strong> in ${item.field}<br>
                        <code>${escapeHtml(item.value)}</code>
                    </div>
                `;
            }
        }

        piiDetailsCard.style.display = 'block';
        document.getElementById('piiDetailsContent').innerHTML = html;
        piiDetailsCard.scrollIntoView({ behavior: 'smooth' });
    };

    // Close PII Details
    if (closePiiDetailsBtn) {
        closePiiDetailsBtn.addEventListener('click', () => {
            piiDetailsCard.style.display = 'none';
        });
    }

    if (complianceExportForm) {
        console.log("Attaching compliance export form listener");
        complianceExportForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            console.log("Compliance form submitted!");
            const tenantId = complianceTenantId.value.trim();
            console.log("Compliance export clicked, tenant:", tenantId);

            if (!tenantId) {
                complianceExportResult.classList.add("show", "error");
                complianceExportResult.innerHTML = `✗ Enter tenant ID`;
                return;
            }

            try {
                complianceExportResult.classList.add("show");
                complianceExportResult.classList.remove("error", "success");
                complianceExportResult.innerHTML = `⏳ Generating compliance pack...`;
                const url = `/compliance/export?tenant_id=${encodeURIComponent(tenantId)}`;
                console.log("Fetching:", url);

                const response = await apiCall(url, 'GET');
                console.log("Response status:", response.status);
                console.log("Response headers:", response.headers);

                if (!response.ok) {
                    console.log("Response not ok, trying to parse as JSON");
                    const text = await response.text();
                    console.log("Response text:", text);
                    try {
                        const error = JSON.parse(text);
                        complianceExportResult.classList.add("error");
                        complianceExportResult.innerHTML = `✗ Error: ${error.error || error.detail || response.statusText}`;
                    } catch {
                        complianceExportResult.classList.add("error");
                        complianceExportResult.innerHTML = `✗ Error: ${response.statusText}`;
                    }
                    return;
                }

                // Download the ZIP file
                console.log("Getting blob...");
                const blob = await response.blob();
                console.log("Blob size:", blob.size);

                const urlObj = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = urlObj;

                // Extract filename from Content-Disposition header if available
                const disposition = response.headers.get('content-disposition');
                let filename = `compliance_export_${tenantId}.zip`;
                if (disposition) {
                    const matches = disposition.match(/filename=([^;]+)/);
                    if (matches && matches[1]) {
                        filename = matches[1].replace(/"/g, '');
                    }
                }

                console.log("Downloading as:", filename);
                a.setAttribute('download', filename);
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(urlObj);
                document.body.removeChild(a);

                complianceExportResult.classList.add("success");
                complianceExportResult.classList.remove("error");
                complianceExportResult.innerHTML = `
                    ✓ Compliance pack downloaded successfully!<br>
                    <small>File: ${filename}</small>
                `;
                complianceExportForm.reset();
            } catch (error) {
                console.error("Export error:", error);
                complianceExportResult.classList.add("error");
                complianceExportResult.classList.remove("success");
                complianceExportResult.innerHTML = `✗ Export failed: ${error.message}`;
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
