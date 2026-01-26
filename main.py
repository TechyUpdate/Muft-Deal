@server.route('/watch')
def watch_page():
    user_id = request.args.get('user_id')
    
    # Monetag link with sub_id for tracking
    ad_link = f"{AD_LINK}?sub_id={user_id}&back_url={SITE_URL}/verify?user_id={user_id}"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
    </head>
    <body style="background:#000; color:white; text-align:center; padding-top:100px;">
        <p>Opening ad...</p>
        <script>
            window.onload = function() {{
                if (window.Telegram?.WebApp) {{
                    window.Telegram.WebApp.openLink("{ad_link}");
                }} else {{
                    window.location.href = "{ad_link}";
                }}
                
                // Wait and redirect
                setTimeout(() => {{
                    window.location.href = "{SITE_URL}/verify?user_id={user_id}";
                }}, 20000);
            }};
        </script>
    </body>
    </html>
    """
    return html
