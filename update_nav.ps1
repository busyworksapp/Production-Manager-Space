$templateDir = "templates"

$oldNavPattern = '(?s)<nav class="nav">\s*<a href="/dashboard"[^>]*>Dashboard</a>\s*<a href="/planning/orders"[^>]*>Planning</a>\s*<a href="/defects/replacement-tickets"[^>]*>Defects</a>\s*<a href="/sop/tickets"[^>]*>SOP & NCR</a>\s*<a href="/maintenance/tickets"[^>]*>Maintenance</a>\s*<a href="/admin/departments"[^>]*>Admin</a>\s*</nav>'

$newNav = '<nav class="nav"></nav>'

$updatedCount = 0

Get-ChildItem -Path $templateDir -Filter *.html -Recurse | Where-Object {
    $_.Name -ne 'login.html' -and $_.Name -ne 'index.html'
} | ForEach-Object {
    $file = $_
    $content = Get-Content $file.FullName -Raw -Encoding UTF8
    
    if ($content -match '<nav class="nav"></nav>') {
        Write-Host "Skipping $($file.Name) - already updated"
        return
    }
    
    if ($content -match $oldNavPattern) {
        $content = $content -replace $oldNavPattern, $newNav
        
        if ($content -notmatch '/static/js/navigation\.js' -and $content -match '/static/js/auth\.js') {
            $content = $content -replace '(<script src="/static/js/auth\.js"></script>)\s*(<script)', "`$1`n    <script src=`"/static/js/navigation.js`"></script>`n    `$2"
        }
        
        Set-Content -Path $file.FullName -Value $content -Encoding UTF8 -NoNewline
        Write-Host "Updated: $($file.FullName)"
        $updatedCount++
    }
}

Write-Host "`nTotal files updated: $updatedCount"
