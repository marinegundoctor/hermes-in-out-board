import re

# 1. Update index.html
with open("templates/index.html", "r") as f:
    html = f.read()

html = html.replace('id="smartcard-content" style="width: 400px; max-width: 90%;"', 'id="smartcard-content" style="width: 700px; max-width: 95%; padding: 40px;"')

with open("templates/index.html", "w") as f:
    f.write(html)

# 2. Update app.js
with open("static/js/app.js", "r") as f:
    js = f.read()

# Clock IN screen
js = js.replace('<h2 style="font-size: 2rem;', '<h2 style="font-size: 3.5rem;')
js = js.replace('<p style="font-size: 1.2rem;">Setting status', '<p style="font-size: 2rem; margin-top: 20px;">Setting status')

# Check OUT screen
js = js.replace('<h2>Check OUT:', '<h2 style="font-size: 3.5rem; margin-bottom: 25px;">Check OUT:')
js = js.replace('font-size: 1.2rem; color: #ccc;"', 'font-size: 2.4rem; color: #ccc; gap: 16px;"')
js = js.replace('<p style="margin-top:15px; color:#888; font-size:1.1rem;">Press option number', '<p style="margin-top:30px; color:#888; font-size:1.8rem;">Press option number')
js = js.replace('<p style="color:#888; font-size:1.1rem;">Press <b>ESC</b>', '<p style="color:#888; font-size:1.8rem; margin-top: 10px;">Press <b>ESC</b>')

# Register Email
js = js.replace('<h2>New Card Detected</h2>', '<h2 style="font-size: 3.5rem; margin-bottom: 20px;">New Card Detected</h2>')
js = js.replace('Please enter your <b>Work Email</b> to link your account, and press <b>Enter</b>:</p>', 'Please enter your <b>Work Email</b> to link your account, and press <b>Enter</b>:</p>').replace('<p style="margin-bottom: 10px;">Please enter', '<p style="margin-bottom: 20px; font-size: 1.8rem;">Please enter')
js = js.replace('style="font-size:1.2rem; padding: 10px; width: 100%;"', 'style="font-size:2rem; padding: 15px; width: 100%;"')

# Custom Location & Comment & Register Name & Group...
js = js.replace('style="font-size:1.4rem; padding: 10px;', 'style="font-size:2rem; padding: 15px;')
js = js.replace('font-size: 1.2rem;">Press <b>Tab</b>', 'font-size: 1.8rem; margin-top: 20px;">Press <b>Tab</b>')
js = js.replace('font-size: 1.4rem;">Press <b>Y</b>', 'font-size: 1.8rem;">Press <b>Y</b>')
js = js.replace('<p style="margin-top:15px; color:#888; font-size:1.1rem;" id="timeout-msg">', '<p style="margin-top:25px; color:#888; font-size:1.8rem;" id="timeout-msg">')
js = js.replace('font-size: 1.2rem; color: #ccc;">`', 'font-size: 2.4rem; color: #ccc; gap: 16px;">`')
js = js.replace('<p style="margin-top:15px; color:#888; font-size:1.1rem;">Press option number.</p>', '<p style="margin-top:30px; color:#888; font-size:1.8rem;">Press option number.</p>')
js = js.replace('font-size: 1.2rem; margin-top: 15px;">Press <b>Enter</b> to submit & Clock IN.</p>', 'font-size: 1.8rem; margin-top: 25px;">Press <b>Enter</b> to submit & Clock IN.</p>')

with open("static/js/app.js", "w") as f:
    f.write(js)
