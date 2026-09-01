with open("static/js/app.js", "r") as f:
    js = f.read()

# Replace backend error styling
old_backend_err = """            document.getElementById('backend-status-dot').style.background = 'var(--status-out)';
            document.getElementById('backend-status-dot').style.boxShadow = '0 0 8px var(--status-out)';
            document.getElementById('backend-status-text').innerText = 'Backend';
            document.getElementById('backend-status-text').style.color = 'var(--status-out)';"""

new_backend_err = """            document.getElementById('backend-status-dot').style.backgroundColor = 'var(--status-out)';
            document.getElementById('backend-status-dot').style.boxShadow = '0 0 8px var(--status-out)';
            document.getElementById('backend-status-text').innerText = 'Backend';
            document.getElementById('backend-status-text').style.color = 'var(--text-muted)';"""
js = js.replace(old_backend_err, new_backend_err)

# Replace backend success styling
old_backend_ok = """            document.getElementById('backend-status-dot').style.background = 'var(--status-in)';
            document.getElementById('backend-status-dot').style.boxShadow = '0 0 8px var(--status-in)';
            document.getElementById('backend-status-text').innerText = 'Backend';
            document.getElementById('backend-status-text').style.color = 'var(--text-muted)';"""

new_backend_ok = """            document.getElementById('backend-status-dot').style.backgroundColor = 'var(--status-in)';
            document.getElementById('backend-status-dot').style.boxShadow = '0 0 8px var(--status-in)';
            document.getElementById('backend-status-text').innerText = 'Backend';
            document.getElementById('backend-status-text').style.color = 'var(--text-muted)';"""
js = js.replace(old_backend_ok, new_backend_ok)


# Replace internet error styling
old_net_err = """            netDot.style.background = 'var(--status-out)';
            netDot.style.boxShadow = '0 0 8px var(--status-out)';
            netText.style.color = 'var(--status-out)';"""

new_net_err = """            netDot.style.backgroundColor = 'var(--status-out)';
            netDot.style.boxShadow = '0 0 8px var(--status-out)';
            netText.style.color = 'var(--text-muted)';"""
js = js.replace(old_net_err, new_net_err)

# Replace internet ok styling
old_net_ok = """            netDot.style.background = 'var(--status-in)';
            netDot.style.boxShadow = '0 0 8px var(--status-in)';
            netText.style.color = 'var(--text-muted)';"""

new_net_ok = """            netDot.style.backgroundColor = 'var(--status-in)';
            netDot.style.boxShadow = '0 0 8px var(--status-in)';
            netText.style.color = 'var(--text-muted)';"""
js = js.replace(old_net_ok, new_net_ok)


with open("static/js/app.js", "w") as f:
    f.write(js)
