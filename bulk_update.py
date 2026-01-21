import os
import glob

template_files = [
    'templates/admin/workflows.html',
    'templates/admin/forms.html',
    'templates/admin/field_permissions.html',
    'templates/admin/employees.html',
    'templates/admin/products.html',
    'templates/admin/machines.html',
    'templates/admin/roles.html',
    'templates/admin/sla.html',
    'templates/admin/d365.html',
    'templates/finance/costs.html',
    'templates/finance/bom.html',
    'templates/defects/customer_returns.html',
    'templates/defects/cost_analysis.html',
    'templates/sop/ticket_detail.html',
    'templates/reports/configuration.html',
    'templates/reports/automation.html',
    'templates/maintenance/preventive.html',
    'templates/maintenance/analytics.html',
    'templates/planning/machine_calendar.html',
    'templates/planning/capacity.html',
    'templates/planning/schedule.html',
    'templates/manager/dashboard.html',
]

nav_replacements = {
    'active">Dashboard': '>Dashboard',
    'active">Planning': '>Planning',
    'active">Defects': '>Defects',
    'active">SOP & NCR': '>SOP & NCR',
    'active">Maintenance': '>Maintenance',
    'active">Admin': '>Admin',
}

def update_file(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original = content
    
    for old, new in nav_replacements.items():
        content = content.replace(old, new)
    
    lines = content.split('\n')
    new_lines = []
    skip_until = 0
    
    for i, line in enumerate(lines):
        if i < skip_until:
            continue
        
        if '<nav class="nav">' in line:
            j = i
            while j < len(lines) and '</nav>' not in lines[j]:
                j += 1
            if j < len(lines):
                new_lines.append('            <nav class="nav"></nav>')
                skip_until = j + 1
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    if '<script src="/static/js/auth.js"></script>' in content and \
       '<script src="/static/js/navigation.js"></script>' not in content:
        content = content.replace(
            '<script src="/static/js/auth.js"></script>',
            '<script src="/static/js/auth.js"></script>\n    <script src="/static/js/navigation.js"></script>'
        )
    
    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    
    return False

updated = 0
for filepath in template_files:
    if update_file(filepath):
        print(f"Updated: {filepath}")
        updated += 1
    else:
        print(f"No changes: {filepath}")

print(f"\nTotal updated: {updated}/{len(template_files)}")
