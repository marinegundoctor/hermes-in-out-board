const fs = require('fs');
let css = fs.readFileSync('static/css/styles.css', 'utf8');
if (!css.includes('.clickable-row')) {
    css += `
/* Kiosk Mode Styles */
body.kiosk-mode .clocks-grid {
    display: none !important;
}
body.kiosk-mode .clickable-row {
    cursor: pointer;
    transition: background 0.2s;
}
body.kiosk-mode .clickable-row:hover, body.kiosk-mode .clickable-row:active {
    background: rgba(255, 255, 255, 0.1);
}
body.kiosk-mode .clickable-row td {
    pointer-events: none;
}
`;
    fs.writeFileSync('static/css/styles.css', css);
}

let js = fs.readFileSync('static/js/app.js', 'utf8');

// Expose handleBadgeTap globally
if (!js.includes('window.handleBadgeTap = handleBadgeTap')) {
    js = js.replace('async function handleBadgeTap(uid) {', 'window.handleBadgeTap = handleBadgeTap;\n    async function handleBadgeTap(uid) {');
}

// Add kiosk mode detection
if (!js.includes('const isKiosk = new URLSearchParams(window.location.search).get("view") === "kiosk";')) {
    js = js.replace('const boardsContainer = document.getElementById(\'boards-container\');', 'const isKiosk = new URLSearchParams(window.location.search).get("view") === "kiosk";\n    if (isKiosk) document.body.classList.add("kiosk-mode");\n    const boardsContainer = document.getElementById(\'boards-container\');');
}

// Add onclick to tr
if (!js.includes('const rowAttr = isKiosk ? `onclick="window.handleBadgeTap(\\'${user.uid}\\')"` : "";')) {
    js = js.replace('tbodyHtml += `\n                    <tr>', 'const rowAttr = isKiosk ? `class="clickable-row" onclick="window.handleBadgeTap(\\'${user.uid}\\')"` : "";\n                tbodyHtml += `\n                    <tr ${rowAttr}>');
}

fs.writeFileSync('static/js/app.js', js);
