import glob
import os

html_files = glob.glob('templates/*.html')

theme_script = """
    <script>
        if (localStorage.getItem('theme') === 'light') {
            document.documentElement.setAttribute('data-theme', 'light');
        }
        function toggleTheme() {
            const isLight = document.documentElement.getAttribute('data-theme') === 'light';
            if (isLight) {
                document.documentElement.removeAttribute('data-theme');
                localStorage.setItem('theme', 'dark');
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
                localStorage.setItem('theme', 'light');
            }
        }
    </script>
</head>
"""

theme_btn = """
            <button id="themeToggle" class="btn-new-analysis" style="background: rgba(124, 77, 255, 0.1); color: var(--text-primary); border-color: rgba(124, 77, 255, 0.3); padding: 8px; width: 36px; height: 36px; display: flex; align-items: center; justify-content: center; border-radius: 50%; margin-right: 12px; cursor: pointer;" aria-label="Toggle theme" onclick="toggleTheme()">
                <svg class="sun-icon" style="display: block;" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>
                <svg class="moon-icon" style="display: none;" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
            </button>
"""

for file in html_files:
    with open(file, 'r') as f:
        content = f.read()

    modified = False

    # Add the script to </head> if not already there
    if "toggleTheme()" not in content:
        content = content.replace("</head>", theme_script)
        modified = True
    
    # Add the button
    if 'id="themeToggle"' not in content:
        if '<div class="user-greeting">' in content:
            content = content.replace('<div class="user-greeting">', theme_btn + '\n            <div class="user-greeting">')
            modified = True
        elif '<div class="header-badge">' in content:
            content = content.replace('<div class="header-badge">', '<div style="display: flex; align-items: center;">\n' + theme_btn + '            <div class="header-badge">')
            # Fix closing div
            content = content.replace('</header>', '</div>\n    </header>')
            modified = True

    if modified:
        with open(file, 'w') as f:
            f.write(content)
        print(f"Updated {file}")
