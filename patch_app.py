import re

with open("static/js/app.js", "r") as f:
    code = f.read()

# 1. Add quickPickTimeout to top level vars
code = re.sub(
    r"(let commentTimeout;)",
    r"\1\nlet quickPickTimeout;",
    code
)

# 2. Modify pollSmartCard
new_poll = """function pollSmartCard() {
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
                    clearTimeout(commentTimeout);
                    clearTimeout(quickPickTimeout);
                    handleCardScanned(data);
                } else if (cardState === 'IDLE') {
                    handleCardScanned(data);
                }
            }
        }).catch(err => console.error("Card poll error", err));
}"""
code = re.sub(
    r"function pollSmartCard\(\) \{[\s\S]*?\}\n\n// Poll every 1\.5 seconds for snappy UI",
    new_poll + "\n\n// Poll every 1.5 seconds for snappy UI",
    code
)

# 3. Modify handleCardScanned for QUICK_PICK
old_quick = """            cardState = 'QUICK_PICK';
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
                <p style="margin-top:30px; color:#888; font-size:1.8rem;">Press option number, or <b>Enter</b> to end of day.</p>
                <p style="color:#888; font-size:1.8rem; margin-top: 10px;">Press <b>ESC</b> to cancel.</p>
            `;"""

new_quick = """            cardState = 'QUICK_PICK';
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
            }, 1000);"""

code = code.replace(old_quick, new_quick)

# 4. Clear quickPickTimeout when card modal closes
old_close = """function closeCardModal() {
    document.getElementById('smartcard-modal').classList.add('hidden');
    cardState = 'IDLE';
    activeCardId = null;
    clearTimeout(commentTimeout);
}"""

new_close = """function closeCardModal() {
    document.getElementById('smartcard-modal').classList.add('hidden');
    cardState = 'IDLE';
    activeCardId = null;
    clearTimeout(commentTimeout);
    clearTimeout(quickPickTimeout);
}"""
code = code.replace(old_close, new_close)

# 5. Fix submitCardAction to capture the cardId being submitted
old_submit = """function submitCardAction(action, loc, comment) {
    fetch('/api/scans/action', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            card_id: activeCardId,
            action: action,
            location: loc,
            comment: comment
        })
    }).then(() => {
        closeCardModal();
        loadData();
    });
}"""

new_submit = """function submitCardAction(action, loc, comment) {
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
}"""
code = code.replace(old_submit, new_submit)


# Cleanup old handleBadgeTap and kiosk variables since they are completely unused now
# Find the start of dev-sim-btn block or kiosk-modal block and remove them.
# The previous delete removed simBtn listeners, but left variables and handleBadgeTap.

with open("static/js/app.js", "w") as f:
    f.write(code)

