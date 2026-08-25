import re

with open("static/js/app.js", "r") as f:
    content = f.read()

# Update tbody row
old_tbody = """
                tbodyHtml += `
                    <tr>
                        <td><strong>${rankDisplay}${escapeHtml(user.name)}</strong></td>
                        <td><span class="status-badge ${user.status}">${statusIcon}</span></td>
                        <td><div class="location-cell">${locationIcon}${escapeHtml(user.location)}</div></td>
                        <td class="comment-cell">${escapeHtml(user.comment)}</td>
                    </tr>
                `;"""

new_tbody = """
                const rDisplay = user.rank ? escapeHtml(user.rank) : '';
                tbodyHtml += `
                    <tr>
                        <td style="color: var(--text-muted); font-weight: 500;">${rDisplay}</td>
                        <td><strong>${escapeHtml(user.name)}</strong></td>
                        <td><span class="status-badge ${user.status}">${statusIcon}</span></td>
                        <td><div class="location-cell">${locationIcon}${escapeHtml(user.location)}</div></td>
                        <td class="comment-cell">${escapeHtml(user.comment)}</td>
                    </tr>
                `;"""

content = content.replace(old_tbody, new_tbody)

# Update thead
old_thead = """
                            <tr>
                                <th style="width: 20%;">NAME</th>
                                <th style="width: 15%;">STATUS</th>
                                <th style="width: 20%;">LOCATION</th>
                                <th style="width: 45%;">COMMENT</th>
                            </tr>"""

new_thead = """
                            <tr>
                                <th style="width: 7%;">RANK</th>
                                <th style="width: 15%;">NAME</th>
                                <th style="width: 15%;">STATUS</th>
                                <th style="width: 18%;">LOCATION</th>
                                <th style="width: 45%;">COMMENT</th>
                            </tr>"""

content = content.replace(old_thead, new_thead)

with open("static/js/app.js", "w") as f:
    f.write(content)
