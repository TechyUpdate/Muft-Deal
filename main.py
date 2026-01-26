@server.route('/watch')
def watch_page():
    user_id = request.args.get('user_id')
    if not user_id:
        return "Error"
    
    # Generate unique session
    import time
    session_id = f"{user_id}_{int(time.time())}"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MoneyTube</title>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body {{
                background: #000;
                color: white;
                font-family: Arial, sans-serif;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
                text-align: center;
            }}
            .spinner {{
                width: 50px;
                height: 50px;
                border: 3px solid #333;
                border-top: 3px solid #00c853;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin-bottom: 20px;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            .btn {{
                background: #00c853;
                color: white;
                border: none;
                padding: 15px 40px;
                font-size: 18px;
                border-radius: 25px;
                cursor: pointer;
                margin-top: 20px;
            }}
            .hidden {{ display: none; }}
        </style>
    </head>
    <body>
        <div id="step1">
            <div class="spinner"></div>
            <p>Preparing ad...</p>
        </div>
        
        <div id="step2" class="hidden">
            <p>👇 Click to open ad</p>
            <button class="btn" onclick="openAd()">▶️ Watch Ad</button>
        </div>
        
        <div id="step3" class="hidden">
            <div class="spinner"></div>
            <p>Ad playing in browser...</p>
            <p style="color: #666; font-size: 14px;">Don't close this window</p>
        </div>

        <script>
            const AD_LINK = "{AD_LINK}";
            const VERIFY_URL = "{SITE_URL}/verify?user_id={user_id}&session={session_id}";
            let checkInterval;
            
            // Init
            window.onload = function() {{
                if (window.Telegram?.WebApp) {{
                    window.Telegram.WebApp.ready();
                    window.Telegram.WebApp.expand();
                }}
                
                // Show button after 1 sec
                setTimeout(() => {{
                    document.getElementById('step1').classList.add('hidden');
                    document.getElementById('step2').classList.add('hidden');
                    document.getElementById('step3').classList.remove('hidden');
                    
                    // Auto open ad
                    openAd();
                }}, 1000);
            }};
            
            function openAd() {{
                // Method 1: Telegram openLink (Best)
                if (window.Telegram?.WebApp?.openLink) {{
                    window.Telegram.WebApp.openLink(AD_LINK);
                }} 
                // Method 2: Try external
                else {{
                    window.open(AD_LINK, '_system');
                }}
                
                // Start checking for completion
                startChecking();
            }}
            
            function startChecking() {{
                // Poll server every 2 seconds to check if ad completed
                checkInterval = setInterval(async () => {{
                    try {{
                        const res = await fetch('{SITE_URL}/check-ad-status?user_id={user_id}');
                        const data = await res.json();
                        
                        if (data.completed) {{
                            clearInterval(checkInterval);
                            window.location.href = VERIFY_URL;
                        }}
                    }} catch(e) {{
                        console.log('Checking...');
                    }}
                }}, 2000);
                
                // Fallback: Auto redirect after 30 seconds
                setTimeout(() => {{
                    clearInterval(checkInterval);
                    window.location.href = VERIFY_URL;
                }}, 30000);
            }}
            
            // When user returns to this tab
            document.addEventListener('visibilitychange', () => {{
                if (!document.hidden) {{
                    // User came back, check immediately
                    fetch('{SITE_URL}/check-ad-status?user_id={user_id}')
                        .then(r => r.json())
                        .then(data => {{
                            if (data.completed) {{
                                window.location.href = VERIFY_URL;
                            }}
                        }});
                }}
            }});
        </script>
    </body>
    </html>
    """
    return html

# Add this route
@server.route('/check-ad-status')
def check_ad_status():
    user_id = request.args.get('user_id')
    # Check if enough time passed (15 sec min)
    if user_id in ad_sessions:
        elapsed = time.time() - ad_sessions[user_id]
        return {'completed': elapsed >= 15}
    return {'completed': False}
