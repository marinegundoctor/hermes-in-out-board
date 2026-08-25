document.addEventListener('DOMContentLoaded', () => {
    const boardsContainer = document.getElementById('boards-container');
    const simBtn = document.getElementById('dev-sim-btn');
    const simModal = document.getElementById('sim-modal');
    const simCancel = document.getElementById('sim-cancel');
    const simSubmit = document.getElementById('sim-submit');
    const simUidInput = document.getElementById('sim-uid');

    const kioskModal = document.getElementById('kiosk-modal');
    const kioskGreeting = document.getElementById('kiosk-greeting');
    const kioskActionText = document.getElementById('kiosk-action-text');
    const kioskOutOptions = document.getElementById('kiosk-out-options');
    const kioskSkipBtn = document.getElementById('kiosk-skip');
    const kioskCustomInput = document.getElementById('kiosk-custom-comment');
    const kioskProgressBar = document.getElementById('kiosk-progress');
    const quickBtns = document.querySelectorAll('.btn-quick');

    let allUsers = [];
    let kioskTimer = null;
    let pendingUid = null;

    function updateClocks() {
        const now = new Date();
        const formatTime = (date, tz) => date.toLocaleTimeString('en-US', { timeZone: tz, hour12: false, hour: '2-digit', minute:'2-digit' });
        const formatDate = (date, tz) => date.toLocaleDateString('en-US', { timeZone: tz, weekday: 'short', month: 'short', day: 'numeric' });
        
        document.getElementById('time-local').innerText = formatTime(now, Intl.DateTimeFormat().resolvedOptions().timeZone);
        document.getElementById('date-local').innerText = formatDate(now, Intl.DateTimeFormat().resolvedOptions().timeZone);
        document.getElementById('time-pdt').innerText = formatTime(now, 'America/Los_Angeles');
        document.getElementById('date-pdt').innerText = formatDate(now, 'America/Los_Angeles');
        document.getElementById('time-edt').innerText = formatTime(now, 'America/New_York');
        document.getElementById('date-edt').innerText = formatDate(now, 'America/New_York');
        document.getElementById('time-utc').innerText = formatTime(now, 'UTC');
        document.getElementById('date-utc').innerText = formatDate(now, 'UTC');
    }
    setInterval(updateClocks, 1000);
    updateClocks();

    async function loadData() {
        try {
            const [usersRes, settingsRes] = await Promise.all([
                fetch('/api/users'),
                fetch('/api/settings')
            ]);
            
            allUsers = await usersRes.json();
            renderTables(allUsers);
            
            if (settingsRes.ok) {
                const settings = await settingsRes.json();
                document.getElementById('news-title').innerText = settings.news_title || '';
                document.getElementById('news-body').innerText = settings.news_body || '';
                document.getElementById('news-author').innerText = settings.news_author || settings.org_name || '';
                document.getElementById('banner-org-name').innerText = settings.org_name || '';
            }
            
            document.getElementById('backend-status-dot').style.background = 'var(--status-in)';
            document.getElementById('backend-status-dot').style.boxShadow = '0 0 8px var(--status-in)';
            document.getElementById('backend-status-text').innerText = 'Backend Active';
            document.getElementById('backend-status-text').style.color = 'var(--text-muted)';
            
        } catch (err) {
            console.error("Failed to load data:", err);
            document.getElementById('backend-status-dot').style.background = 'var(--status-out)';
            document.getElementById('backend-status-dot').style.boxShadow = '0 0 8px var(--status-out)';
            document.getElementById('backend-status-text').innerText = 'Backend Offline';
            document.getElementById('backend-status-text').style.color = 'var(--status-out)';
        }
    }

    function renderTables(users) {
        boardsContainer.innerHTML = '';
        const groups = new Map();
        users.forEach(u => {
            const g = u.group_name || "Unassigned";
            if (!groups.has(g)) groups.set(g, []);
            groups.get(g).push(u);
        });

        for (const [groupName, members] of groups.entries()) {
            let inCount = 0;
            let outCount = 0;
            let tbodyHtml = '';

            members.forEach(user => {
                if (user.status === 'in') inCount++;
                else outCount++;

                const statusIcon = user.status === 'in' ? '<i class="fa-solid fa-circle"></i> IN' : '<i class="fa-solid fa-circle"></i> OUT';
                const locationIcon = user.location === '--' ? '' : '<i class="fa-solid fa-building"></i> ';
                const rankDisplay = user.rank ? escapeHtml(user.rank) + ' ' : '';

                const rDisplay = user.rank ? escapeHtml(user.rank) : '';
                tbodyHtml += `
                    <tr>
                        <td style="color: var(--text-muted); font-weight: 500;">${rDisplay}</td>
                        <td><strong>${escapeHtml(user.name)}</strong></td>
                        <td><span class="status-badge ${user.status}">${statusIcon}</span></td>
                        <td><div class="location-cell">${locationIcon}${escapeHtml(user.location)}</div></td>
                        <td class="comment-cell">${escapeHtml(user.comment)}</td>
                    </tr>
                `;
            });
            const section = document.createElement('section');
            section.className = 'panel board-panel';
            section.style.marginBottom = '20px';
            section.innerHTML = `
                <div class="board-header">
                    <div class="title-with-icon">
                        <i class="fa-solid fa-users"></i>
                        <h3>${escapeHtml(groupName)}</h3>
                    </div>
                    <div class="board-filters">
                        <button class="filter-btn count-in"><span>${inCount}</span> IN</button>
                        <button class="filter-btn count-out"><span>${outCount}</span> OUT</button>
                    </div>
                </div>
                <div class="table-container">
                    <table class="employee-table">
                        <thead>
                            <tr>
                                <th style="width: 7%;">RANK</th>
                                <th style="width: 15%;">NAME</th>
                                <th style="width: 15%;">STATUS</th>
                                <th style="width: 18%;">LOCATION</th>
                                <th style="width: 45%;">COMMENT</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${tbodyHtml}
                        </tbody>
                    </table>
                </div>
            `;
            boardsContainer.appendChild(section);
        }
    }

    function escapeHtml(unsafe) {
        if (!unsafe) return '';
        return String(unsafe).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    }

    simBtn.addEventListener('click', () => {
        simModal.classList.remove('hidden');
        simUidInput.focus();
    });

    const closeSimModal = () => {
        simModal.classList.add('hidden');
        simUidInput.value = '';
    };
    simCancel.addEventListener('click', closeSimModal);
    simSubmit.addEventListener('click', () => {
        const uid = simUidInput.value.trim();
        if (!uid) return;
        closeSimModal();
        handleBadgeTap(uid);
    });

    async function handleBadgeTap(uid) {
        const user = allUsers.find(u => String(u.uid) === String(uid));
        if (!user) {
            alert("User with badge not found!");
            return;
        }

        pendingUid = uid;
        kioskModal.classList.remove('hidden');
        kioskGreeting.innerText = `Hello, ${user.name}!`;
        kioskCustomInput.value = '';

        if (user.status === 'out') {
            kioskActionText.innerText = "Checking IN... Welcome back!";
            kioskActionText.style.color = 'var(--status-in)';
            kioskOutOptions.classList.add('hidden');
            kioskSkipBtn.classList.add('hidden');
            startKioskTimer(3000, true);
        } else {
            kioskActionText.innerText = "Checking OUT.";
            kioskActionText.style.color = 'var(--status-out)';
            kioskOutOptions.classList.remove('hidden');
            kioskSkipBtn.classList.remove('hidden');
            startKioskTimer(10000, true);
        }
    }

    function startKioskTimer(duration, autoSubmit) {
        if (kioskTimer) clearInterval(kioskTimer);
        const updateInterval = 50;
        let elapsed = 0;
        kioskTimer = setInterval(() => {
            elapsed += updateInterval;
            let percent = 100 - ((elapsed / duration) * 100);
            kioskProgressBar.style.width = `${Math.max(0, percent)}%`;
            if (elapsed >= duration) {
                clearInterval(kioskTimer);
                if (autoSubmit) submitKioskData();
                else resetKiosk();
            }
        }, updateInterval);
    }

    kioskCustomInput.addEventListener('input', () => {
        if (kioskTimer) clearInterval(kioskTimer);
        kioskProgressBar.style.width = '100%';
        kioskProgressBar.style.background = '#0284c7';
    });

    quickBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            submitKioskData(e.target.getAttribute('data-val'), ""); 
        });
    });

    kioskSkipBtn.addEventListener('click', () => {
        submitKioskData(kioskCustomInput.value.trim() ? "Unknown" : "--", kioskCustomInput.value.trim());
    });

    async function submitKioskData(locationVal = "--", commentVal = "") {
        if (kioskTimer) clearInterval(kioskTimer);
        if (!commentVal && kioskCustomInput.value.trim()) {
            commentVal = kioskCustomInput.value.trim();
            locationVal = "Unknown";
        }
        try {
            const res = await fetch('/api/tap', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ uid: pendingUid, location: locationVal, comment: commentVal })
            });
            if (res.ok) loadData();
        } catch (err) {}
        resetKiosk();
    }

    function resetKiosk() {
        if (kioskTimer) clearInterval(kioskTimer);
        kioskModal.classList.add('hidden');
        pendingUid = null;
        kioskProgressBar.style.background = 'var(--accent-yellow)';
    }

    loadData();
    setInterval(loadData, 5000);
});
