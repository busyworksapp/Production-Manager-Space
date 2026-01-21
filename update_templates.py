import os
import re
from pathlib import Path

template_dir = Path('templates')

old_nav_pattern = re.compile(
    r'<nav class="nav">\s*'
    r'<a href="/dashboard"[^>]*>Dashboard</a>\s*'
    r'<a href="/planning/orders"[^>]*>Planning</a>\s*'
    r'<a href="/defects/replacement-tickets"[^>]*>Defects</a>\s*'
    r'<a href="/sop/tickets"[^>]*>SOP & NCR</a>\s*'
    r'<a href="/maintenance/tickets"[^>]*>Maintenance</a>\s*'
    r'<a href="/admin/departments"[^>]*>Admin</a>\s*'
    r'</nav>',
    re.DOTALL | re.MULTILINE
)

new_nav = '<nav class="nav"></nav>'

script_pattern = re.compile(
    r'(<script src="/static/js/auth\.js"></script>)\s*'
    r'(<script)',
    re.MULTILINE
)

new_scripts = r'\1\n    <script src="/static/js/navigation.js"></script>\n    \2'

def update_template(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    if file_path.name in ['login.html', 'index.html']:
        return False
    
    if '<nav class="nav"></nav>' in content:
        return False
    
    content = old_nav_pattern.sub(new_nav, content)
    
    if '/static/js/navigation.js' not in content and '/static/js/auth.js' in content:
        content = script_pattern.sub(new_scripts, content)
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    
    return False

def main():
    updated_files = []
    
    for html_file in template_dir.rglob('*.html'):
        if update_template(html_file):
            updated_files.append(str(html_file))
            print(f'Updated: {html_file}')
    
    print(f'\nTotal files updated: {len(updated_files)}')
    
    if updated_files:
        print('\nUpdated files:')
        for file in updated_files:
            print(f'  - {file}')

if __name__ == '__main__':
    main()
