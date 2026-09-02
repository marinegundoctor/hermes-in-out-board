
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return String(unsafe).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
document.addEventListener('DOMContentLoaded', () => {
    const isKiosk = new URLSearchParams(window.location.search).get("view") === "kiosk";
    if (isKiosk) document.body.classList.add("kiosk-mode");
    const boardsContainer = document.getElementById('boards-container');

    const kioskModal = document.getElementById('kiosk-modal');
    const kioskGreeting = document.getElementById('kiosk-greeting');
    const kioskActionText = document.getElementById('kiosk-action-text');
    const kioskOutOptions = document.getElementById('kiosk-out-options');
    const kioskSkipBtn = document.getElementById('kiosk-skip');
    const kioskCancelBtn = document.getElementById('kiosk-cancel');
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
        // Check Internet Status
        const netDot = document.getElementById('internet-status-dot');
        const netText = document.getElementById('internet-status-text');
        if (netDot && netText) {
            if (navigator.onLine) {
                let isSlow = false;
                if (navigator.connection && navigator.connection.effectiveType) {
                    const et = navigator.connection.effectiveType;
                    if (et === 'slow-2g' || et === '2g' || et === '3g') {
                        isSlow = true;
                    }
                }
                
                if (isSlow) {
                    netDot.style.background = 'var(--accent-yellow)';
                    netDot.style.boxShadow = '0 0 8px var(--accent-yellow)';
                    netText.style.color = 'var(--accent-yellow)';
                } else {
                    netDot.style.background = 'var(--status-in)';
                    netDot.style.boxShadow = '0 0 8px var(--status-in)';
                    netText.style.color = 'var(--text-muted)';
                }
            } else {
                netDot.style.background = 'var(--status-out)';
                netDot.style.boxShadow = '0 0 8px var(--status-out)';
                netText.style.color = 'var(--status-out)';
            }
        }
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
            
            document.getElementById('backend-status-dot').style.backgroundColor = 'var(--status-in)';
            document.getElementById('backend-status-dot').style.boxShadow = '0 0 8px var(--status-in)';
            document.getElementById('backend-status-text').innerText = 'Backend';
            document.getElementById('backend-status-text').style.color = 'var(--text-muted)';
            
        } catch (err) {
            console.error("Failed to load data:", err);
            document.getElementById('backend-status-dot').style.backgroundColor = 'var(--status-out)';
            document.getElementById('backend-status-dot').style.boxShadow = '0 0 8px var(--status-out)';
            document.getElementById('backend-status-text').innerText = 'Backend';
            document.getElementById('backend-status-text').style.color = 'var(--text-muted)';
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
                const rowAttr = isKiosk ? `class="clickable-row" onclick="window.handleBadgeTap('${user.uid}')" onpointerdown="window.handleBadgeTap('${user.uid}')"` : "";
                tbodyHtml += `
                    <tr ${rowAttr}>
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




    window.handleBadgeTap = handleBadgeTap;
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
            startKioskTimer(6000, true);
        } else {
            kioskActionText.innerText = "Checking OUT.";
            kioskActionText.style.color = 'var(--status-out)';
            kioskOutOptions.classList.remove('hidden');
            kioskSkipBtn.classList.remove('hidden');
            startKioskTimer(20000, true);
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

    kioskCancelBtn.addEventListener('click', () => {
        resetKiosk();
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
        if (window.kioskKeyboard) {
            window.kioskKeyboard.clearInput();
        }
        kioskProgressBar.style.background = 'var(--accent-yellow)';
    }

    // Initialize Virtual Keyboard if library is loaded
    if (window.SimpleKeyboard) {
        const Keyboard = window.SimpleKeyboard.default;
        window.kioskKeyboard = new Keyboard({
            onChange: input => {
                kioskCustomInput.value = input;
                // reset timer if they are typing
                startKioskTimer(15000, false);
            },
            onKeyPress: button => {
                if (button === "{enter}") {
                    kioskSkipBtn.click();
                }
            },
            layout: {
                'default': [
                    'q w e r t y u i o p',
                    'a s d f g h j k l',
                    '{shift} z x c v b n m {bksp}',
                    '{space} {enter}'
                ],
                'shift': [
                    'Q W E R T Y U I O P',
                    'A S D F G H J K L',
                    '{shift} Z X C V B N M {bksp}',
                    '{space} {enter}'
                ]
            }
        });
    }

    loadData();
    setInterval(loadData, 5000);
});

    window.addEventListener('online', () => {
        const netDot = document.getElementById('internet-status-dot');
        const netText = document.getElementById('internet-status-text');
        if (netDot && netText) {
            netDot.style.backgroundColor = 'var(--status-in)';
            netDot.style.boxShadow = '0 0 8px var(--status-in)';
            netText.style.color = 'var(--text-muted)';
        }
    });

    window.addEventListener('offline', () => {
        const netDot = document.getElementById('internet-status-dot');
        const netText = document.getElementById('internet-status-text');
        if (netDot && netText) {
            netDot.style.backgroundColor = 'var(--status-out)';
            netDot.style.boxShadow = '0 0 8px var(--status-out)';
            netText.style.color = 'var(--text-muted)';
        }
    });


// --- SMART CARD LOGIC ---
let cardState = 'IDLE'; // IDLE, REGISTER_EMAIL, REGISTER_NAME, QUICK_PICK, COMMENT, CUSTOM_LOC
let activeCardId = null;
let currentQuickPick = null;
let commentTimeout = null;
let quickPickTimeout = null;
let registerTimeout = null;
let registerTimeLeft = 15;

function resetRegisterTimeout() {
    if (registerTimeout) clearInterval(registerTimeout);
    registerTimeLeft = 15;
    
    const updateMsg = () => {
        const msg = document.getElementById('new-user-timeout-msg');
        if (msg) msg.innerText = `Auto-closing in ${registerTimeLeft} seconds...`;
    };
    
    updateMsg();
    registerTimeout = setInterval(() => {
        registerTimeLeft--;
        updateMsg();
        if (registerTimeLeft <= 0) {
            clearInterval(registerTimeout);
            if (cardState.startsWith('REGISTER_')) {
                cancelCard();
            }
        }
    }, 1000);
}

let newUserName = '';
let newUserRank = '';
let newUserEmail = '';
let availableGroups = [];

const QUICK_PICK_MAP = {
    '0': { loc: '--', needsComment: false },
    '1': { loc: 'LUNCH', needsComment: false },
    '2': { loc: 'SUPPLY', needsComment: true },
    '3': { loc: 'JFHQ', needsComment: true },
    '4': { loc: 'G6', needsComment: true },
    '5': { loc: 'LEAVE', needsComment: true },
    '6': { loc: 'TDY', needsComment: true },
    '7': { loc: 'Free Text', needsCustom: true }
};

function pollSmartCard() {
    fetch('/api/scans/pending')
        .then(res => res.json())
        .then(data => {
            if (data && data.card_id) {
                if (cardState !== 'IDLE' && activeCardId && activeCardId !== data.card_id) {
                    // Interrupt current flow with new badge
                    const oldCardId = activeCardId;
                    if (['QUICK_PICK', 'COMMENT', 'CUSTOM_LOC'].includes(cardState)) {
                        fetch('/api/scans/action', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({card_id: oldCardId, action: 'OUT', location: '--', comment: '--'})
                        }).then(() => loadData());
                    } else if (cardState.startsWith('REGISTER_')) {
                        fetch('/api/scans/cancel', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({card_id: oldCardId})
                        });
                    }
                    clearInterval(commentTimeout);
                    clearInterval(quickPickTimeout);
                    handleCardScanned(data);
                } else if (cardState === 'IDLE') {
                    handleCardScanned(data);
                }
            }
        }).catch(err => console.error("Card poll error", err));
}

// Poll every 1.5 seconds for snappy UI
setInterval(pollSmartCard, 1500);

function handleCardScanned(data) {
    activeCardId = data.card_id;
    const modal = document.getElementById('smartcard-modal');
    const content = document.getElementById('smartcard-content');
    modal.classList.remove('hidden');
    
    if (data.user) {
        if (data.user.status === 'out') {
            // Clock IN
            content.innerHTML = `
                <div style="text-align: center;">
                    <h2 style="font-size: 3.5rem; color: var(--status-in);"><i class="fa-solid fa-check-circle"></i> Welcome Back, ${escapeHtml(data.user.name)}!</h2>
                    <p style="font-size: 2rem; margin-top: 20px;">Setting status to <b>IN</b>...</p>
                </div>
            `;
            setTimeout(() => {
                submitCardAction('IN', '', '');
            }, 1500);
        } else {
            // Currently IN, prompt for OUT
            cardState = 'QUICK_PICK';
            content.innerHTML = `
                <h2 style="font-size: 3.5rem; margin-bottom: 25px;">Check OUT: ${escapeHtml(data.user.name)}</h2>
                <div style="display: flex; flex-direction: column; gap: 8px; font-size: 2.4rem; color: #ccc; gap: 16px;">
                    <div><b style="color:var(--accent-yellow);">1</b> - LUNCH</div>
                    <div><b style="color:var(--accent-yellow);">2</b> - SUPPLY</div>
                    <div><b style="color:var(--accent-yellow);">3</b> - JFHQ</div>
                    <div><b style="color:var(--accent-yellow);">4</b> - G6</div>
                    <div><b style="color:var(--accent-yellow);">5</b> - LEAVE</div>
                    <div><b style="color:var(--accent-yellow);">6</b> - TDY</div>
                    <div><b style="color:var(--accent-yellow);">7</b> - Free Text</div>
                    <div><b style="color:var(--accent-yellow);">0</b> - End of Day (Blank OUT)</div>
                </div>
                <p style="margin-top:30px; color:#888; font-size:1.8rem;" id="quick-timeout-msg">Auto-submitting in 7 seconds...</p>
                <p style="color:#888; font-size:1.8rem; margin-top: 10px;">Press option number, <b>Enter</b>, or wait.</p>
                <p style="color:#888; font-size:1.8rem; margin-top: 10px;">Press <b>ESC</b> to cancel.</p>
            `;
            let timeLeft = 7;
            if (quickPickTimeout) clearInterval(quickPickTimeout);
            quickPickTimeout = setInterval(() => {
                timeLeft--;
                const msg = document.getElementById('quick-timeout-msg');
                if (msg) msg.innerText = `Auto-submitting in ${timeLeft} seconds...`;
                if (timeLeft <= 0) {
                    clearInterval(quickPickTimeout);
                    if (cardState === 'QUICK_PICK') {
                        submitCardAction('OUT', '--', '--');
                    }
                }
            }, 1000);
        }
    } else {
        // Unknown card, prompt for email
        cardState = 'REGISTER_EMAIL';
        content.innerHTML = `
            <h2 style="font-size: 3.5rem; margin-bottom: 20px;">New Card Detected</h2>
            <p style="margin-bottom: 20px; font-size: 1.8rem;">Please enter your <b>Work Email</b> to link your account, and press <b>Enter</b>:</p>
            <input type="email" id="card-email" placeholder="john.doe@example.com" style="font-size:2rem; padding: 15px; width: 100%;">
            <p style="margin-top:20px; color:#888; font-size:1.5rem;" id="new-user-timeout-msg">Auto-closing in 15 seconds...</p>
            <div class="modal-actions">
                <button class="btn-cancel" onclick="cancelCard()">Cancel</button>
            </div>
        `;
        setTimeout(() => document.getElementById('card-email').focus(), 100);
        resetRegisterTimeout();
    }
}

function cancelCard() {
    if (activeCardId) {
        fetch('/api/scans/cancel', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({card_id: activeCardId})
        });
    }
    closeCardModal();
}


function submitRegistration(groupName) {
    fetch('/api/scans/register_new', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({card_id: activeCardId, email: newUserEmail, name: newUserName, rank: newUserRank, group: groupName})
    }).then(res => res.json()).then(data => {
        if (data.success) {
            const content = document.getElementById('smartcard-content');
            content.innerHTML = `<h2 style="color:var(--status-in);"><i class="fa-solid fa-check"></i> Account Created & Clocked IN!</h2>`;
            setTimeout(() => { closeCardModal(); loadData(); }, 2000);
        }
    });
}

function closeCardModal() {
    document.getElementById('smartcard-modal').classList.add('hidden');
    cardState = 'IDLE';
    activeCardId = null;
    clearInterval(commentTimeout);
    clearInterval(quickPickTimeout);
    clearInterval(registerTimeout);
}

function submitCardAction(action, loc, comment) {
    const submittingCardId = activeCardId;
    fetch('/api/scans/action', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            card_id: submittingCardId,
            action: action,
            location: loc,
            comment: comment
        })
    }).then(() => {
        if (activeCardId === submittingCardId || activeCardId === null) {
            closeCardModal();
        }
        loadData();
    });
}

document.addEventListener('keydown', (e) => {
    if (cardState === 'IDLE') return;
    
    if (cardState.startsWith('REGISTER_')) {
        resetRegisterTimeout();
    }
    
    if (e.key === 'Escape') {
        cancelCard();
        return;
    }

    if (cardState === 'QUICK_PICK') {
        let selection = QUICK_PICK_MAP[e.key];
        
        // Enter defaults to 0 (End of Day)
        if (e.key === 'Enter') {
            selection = QUICK_PICK_MAP['0'];
        }

        if (selection) {
            currentQuickPick = selection;
            
            if (currentQuickPick.needsCustom) {
                cardState = 'CUSTOM_LOC';
                const content = document.getElementById('smartcard-content');
                content.innerHTML = `
                    <h2 style="font-size: 3.5rem; margin-bottom: 10px;">Custom Location</h2>
                    <div style="display: flex; flex-direction: column; gap: 10px; margin-bottom: 15px;">
                        <input type="text" id="custom-loc" placeholder="Enter Location... (Required)" style="font-size:2rem; padding: 15px; width:100%; box-sizing: border-box;" required>
                        <input type="text" id="custom-comment" placeholder="Enter Comment... (Optional)" style="font-size:2rem; padding: 15px; width:100%; box-sizing: border-box;">
                    </div>
                    <p style="color: #ccc; font-size: 1.8rem; margin-top: 20px;">Press <b>Tab</b> to switch fields, <b>Enter</b> to submit.</p>
                `;
                setTimeout(() => document.getElementById('custom-loc').focus(), 100);
            } else if (currentQuickPick.needsComment) {
                cardState = 'COMMENT';
                const content = document.getElementById('smartcard-content');
                content.innerHTML = `
                    <h2 style="font-size: 3.5rem;">Add Comment for ${currentQuickPick.loc}?</h2>
                    <p style="color: #ccc; margin-bottom:15px; font-size: 1.8rem;">Press <b>Y</b> to type a comment, or <b>Enter</b> to skip.</p>
                    <div id="comment-box" class="hidden">
                        <input type="text" id="card-comment" maxlength="140" placeholder="Type comment..." style="font-size:2rem; padding: 15px; width: 100%; box-sizing: border-box;">
                    </div>
                    <p style="margin-top:25px; color:#888; font-size:1.8rem;" id="timeout-msg">Auto-submitting in 10 seconds...</p>
                `;
                
                let timeLeft = 10;
                commentTimeout = setInterval(() => {
                    timeLeft--;
                    const msg = document.getElementById('timeout-msg');
                    if (msg) msg.innerText = `Auto-submitting in ${timeLeft} seconds...`;
                    if (timeLeft <= 0) {
                        clearInterval(commentTimeout);
                        submitCardAction('OUT', currentQuickPick.loc, '--');
                    }
                }, 1000);
                
            } else {
                // Doesn't need comment
                submitCardAction('OUT', currentQuickPick.loc, '--');
            }
        }
    } else if (cardState === 'CUSTOM_LOC') {
        if (e.key === 'Enter') {
            const locInput = document.getElementById('custom-loc').value.trim();
            const cmtInput = document.getElementById('custom-comment').value.trim();
            if (locInput) {
                submitCardAction('OUT', locInput, cmtInput || '--');
            } else {
                document.getElementById('custom-loc').style.border = '2px solid red';
            }
        }
    } else if (cardState === 'COMMENT') {
        const commentBox = document.getElementById('comment-box');
        const input = document.getElementById('card-comment');
        
        if (commentBox.classList.contains('hidden')) {
            if (e.key.toLowerCase() === 'y') {
                clearInterval(commentTimeout);
                document.getElementById('timeout-msg').style.display = 'none';
                commentBox.classList.remove('hidden');
                setTimeout(() => input.focus(), 10);
            } else if (e.key === 'Enter') {
                clearInterval(commentTimeout);
                submitCardAction('OUT', currentQuickPick.loc, '--');
            }
        } else {
            if (e.key === 'Enter') {
                submitCardAction('OUT', currentQuickPick.loc, input.value || '--');
            }
        }
    } else if (cardState === 'REGISTER_EMAIL') {
        if (e.key === 'Enter') {
            const email = document.getElementById('card-email').value;
            if (!email) return;
            
            fetch('/api/scans/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({card_id: activeCardId, email: email})
            }).then(res => res.json()).then(data => {
                if (data.success) {
                    const content = document.getElementById('smartcard-content');
                    content.innerHTML = `<h2 style="color:var(--status-in);"><i class="fa-solid fa-check"></i> ${data.message}</h2>`;
                    setTimeout(() => { closeCardModal(); loadData(); }, 2000);
                } else if (data.needs_name) {
                    cardState = 'REGISTER_NAME';
                    newUserEmail = email;
                    const content = document.getElementById('smartcard-content');
                    content.innerHTML = `
                        <h2 style="margin-bottom: 10px;">Email Not Found</h2>
                        <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                            <input type="text" id="card-rank" placeholder="Rank (Optional)" style="font-size:2rem; padding: 15px; width:40%; box-sizing: border-box;">
                            <input type="text" id="card-name" placeholder="Full Name (Req)" style="font-size:2rem; padding: 15px; width:60%; box-sizing: border-box;" required>
                        </div>
                        <p style="color: #ccc; font-size: 1.8rem; margin-top: 20px;">Press <b>Tab</b> to switch, <b>Enter</b> to continue.</p>
                        <p style="margin-top:20px; color:#888; font-size:1.5rem;" id="new-user-timeout-msg">Auto-closing in 15 seconds...</p>
                    `;
                    setTimeout(() => document.getElementById('card-rank').focus(), 100);
                    resetRegisterTimeout();
                }
            });
        }
    } else if (cardState === 'REGISTER_NAME') {
        if (e.key === 'Enter') {
            const name = document.getElementById('card-name').value.trim();
            const rank = document.getElementById('card-rank').value.trim();
            if (!name) {
                document.getElementById('card-name').style.border = '2px solid red';
                return;
            }
            newUserName = name;
            newUserRank = rank;
            
            availableGroups = Array.from(document.querySelectorAll('.group-header h3'))
                                   .map(h => h.innerText)
                                   .filter(g => g !== 'Unassigned');
            availableGroups = [...new Set(availableGroups)];
            
            cardState = 'REGISTER_GROUP';
            
            let groupHtml = `<h2 style="font-size: 3.5rem;">Select Group</h2>
                             <div style="display: flex; flex-direction: column; gap: 8px; font-size: 2.4rem; color: #ccc; gap: 16px;">`;
            
            availableGroups.forEach((g, idx) => {
                groupHtml += `<div><b style="color:var(--accent-yellow);">${idx + 1}</b> - ${escapeHtml(g)}</div>`;
            });
            groupHtml += `<div><b style="color:var(--accent-yellow);">0</b> - Create New Group</div>
                          </div>
                          <p style="margin-top:30px; color:#888; font-size:1.8rem;">Press option number.</p>
                          <p style="margin-top:20px; color:#888; font-size:1.5rem;" id="new-user-timeout-msg">Auto-closing in 15 seconds...</p>`;
            
            document.getElementById('smartcard-content').innerHTML = groupHtml;
            resetRegisterTimeout();
        }
    } else if (cardState === 'REGISTER_GROUP') {
        if (e.key === '0') {
            cardState = 'REGISTER_GROUP_NEW';
            document.getElementById('smartcard-content').innerHTML = `
                <h2 style="margin-bottom: 10px;">Create New Group</h2>
                <input type="text" id="card-group-new" placeholder="New Group Name" style="font-size:2rem; padding: 15px; width:100%; box-sizing: border-box;" required>
                <p style="color: #ccc; font-size: 1.8rem; margin-top: 25px;">Press <b>Enter</b> to submit & Clock IN.</p>
                <p style="margin-top:20px; color:#888; font-size:1.5rem;" id="new-user-timeout-msg">Auto-closing in 15 seconds...</p>
            `;
            setTimeout(() => document.getElementById('card-group-new').focus(), 100);
            resetRegisterTimeout();
        } else {
            const idx = parseInt(e.key);
            if (!isNaN(idx) && idx >= 1 && idx <= availableGroups.length) {
                submitRegistration(availableGroups[idx - 1]);
            }
        }
    } else if (cardState === 'REGISTER_GROUP_NEW') {
        if (e.key === 'Enter') {
            const grp = document.getElementById('card-group-new').value.trim();
            if (!grp) {
                document.getElementById('card-group-new').style.border = '2px solid red';
                return;
            }
            submitRegistration(grp);
        }
    }
});
