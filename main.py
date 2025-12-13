import os
import time
import requests
import feedparser
import smtplib
import re
import markdown
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from time import mktime

# --- 🐦 Twitter Accounts to Track ---
ACCOUNTS = [
    "deepseek_ai", "NotebookLM", "perplexity_ai", "Alibaba_Qwen", 
    "Starlink", "NASAScience_", "Space_Station", "Erdayastronaut", 
    "SpaceX", "sundarpichai", "grok", "OpenAI", "GoogleDeepMind", "IndianTechGuide",
    "GeminiApp", "BillGates", "xai", "sama", "ChinaScience", 
    "elonmusk", "NASA", "GoogleAIStudio", "joshwoodward", 
    "GoogleLabs", "DeepLearningAI", "NanoBanana", "comet", 
    "arena", "ChatGPTapp", "testingcatalog", "isro", "OpenRouterAI"
]

# --- 🌍 Nitter Instances ---
NITTER_INSTANCES = [
    "https://nitter.privacyredirect.com",
    "https://nitter.poast.org",
    "https://xcancel.com",
    "https://lightbrd.com",
    "https://nitter.space",
    "https://nitter.tiekoetter.com",
    "https://nuku.trabun.org",
    "https://nitter.catsarch.com",
    "https://rss.xcancel.com",
    "https://nitter.lucabased.xyz",
    "https://nitter.net",
    "https://nitter.cz",
    "https://nitter.it",
    "https://nitter.privacydev.net",
    "https://nitter.projectsegfau.lt",
    "https://nitter.eu",
    "https://nitter.soopy.moe",
    "https://nitter.rawbit.ninja",
    "https://nitter.d420.de",
    "https://nitter.x86-64-unknown-linux-gnu.zip",
    "https://nitter.moomoo.me",
    "https://nitter.woodland.cafe",
    "https://nitter.no-logs.com",
    "https://nitter.perennialte.ch",
    "https://nitter.freeredit.eu",
    "https://nitter.adminforge.de"
]

# --- Setup Keys (No Telegram) ---
PERPLEXITY_KEY = os.environ.get("PERPLEXITY_API_KEY", "").strip().replace('"', '')
EMAIL_USER = os.environ.get("EMAIL_USER", "").strip().replace('"', '')
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "").strip().replace('"', '')
EMAIL_RECIPIENT = os.environ.get("EMAIL_RECIPIENT", "").strip().replace('"', '')

# --- 1. Find Working Nitter Instance ---
def get_working_nitter_instance():
    print("🔍 Searching for a working Nitter instance...")
    headers = {"User-Agent": "Mozilla/5.0 (Compatible; RSS Reader)"}

    for url in NITTER_INSTANCES:
        try:
            print(f"Testing {url}...", end=" ", flush=True)
            test_url = f"{url}/NASA/rss"
            response = requests.get(test_url, headers=headers, timeout=5)

            if response.status_code == 200:
                if response.content.strip().startswith(b"<?xml") or b"<rss" in response.content:
                    feed = feedparser.parse(response.content)
                    if feed.entries:
                        if "whitelisted" in feed.entries[0].title.lower() or "rate limit" in feed.entries[0].title.lower():
                            print("❌ (Blocked)")
                            continue
                        print(f"✅ Works!")
                        return url
            print("❌")
        except:
            print("❌")
    return None

# --- 2. Fetch Tweets ---
def get_twitter_updates():
    nitter_url = get_working_nitter_instance()
    if not nitter_url:
        print("⚠️ Critical: No working Nitter instances found. Aborting.")
        return None

    print(f"🐦 Fetching Tweets using {nitter_url}...")
    all_tweets = ""
    headers = {"User-Agent": "Mozilla/5.0 (Compatible; RSS Reader)"}
    yesterday = datetime.now() - timedelta(hours=24)

    for account in ACCOUNTS:
        try:
            rss_url = f"{nitter_url}/{account}/rss"
            response = requests.get(rss_url, headers=headers, timeout=10)
            if response.status_code != 200: continue

            feed = feedparser.parse(response.content)
            account_tweets = []
            
            if feed.entries:
                for entry in feed.entries:
                    if hasattr(entry, 'published_parsed'):
                        published_dt = datetime.fromtimestamp(mktime(entry.published_parsed))
                        if published_dt > yesterday:
                            tweet_text = entry.description if 'description' in entry else entry.title
                            clean_text = re.sub(r'<[^>]+>', '', tweet_text) 
                            account_tweets.append(f"- {clean_text}")

            if account_tweets:
                print(f"✅ @{account}: {len(account_tweets)} new tweets")
                all_tweets += f"\n📢 **@{account}**:\n" + "\n".join(account_tweets[:3])
            time.sleep(1)
        except Exception as e:
            print(f"❌ Error checking @{account}: {e}")

    return all_tweets

# --- 3. Generate Summary (Perplexity Sonar Pro) ---
def generate_summary(tweets_text):
    if not tweets_text: return None

    print("Generating Smart Digest (Perplexity Sonar Pro)...")

    prompt = f"""
    You are a Tech Intelligence Agent. Here are the latest tweets from key tech accounts collected over the last 24 hours:
    
    {tweets_text}
    
    INSTRUCTIONS:
    1. Analyze these tweets and identify the most significant tech news.
    2. Create a **"Daily Tech Briefing"** organized by category (e.g., ## AI & Models, ## Space & Aviation, ## Big Tech).
    3. For each news item, use a bullet point (*). Start with a **Bold Title** followed by a concise summary.
    4. Use emojis where appropriate to make it engaging.
    5. **CRITICAL:** Remove all citation markers like [1], [2], etc. Do not include references.
    6. Do not use Markdown tables.
    
    Example format:
    ## Category Name 🚀
    * **Title of the News:** Summary of what happened...
    * **Another News Item:** Description...
    """

    url = "https://api.perplexity.ai/chat/completions"
    payload = {
        "model": "sonar-pro",
        "messages": [
            {
                "role": "system",
                "content": "Be precise, concise, and follow formatting instructions strictly."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_KEY}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"AI Error: {e}")
        return None

# --- 4. Send Email ---
def markdown_to_html(text):
    if not text: return ""

    # Clean up any potential leftover citation markers just in case
    text = re.sub(r'\[\d+\]', '', text)

    # Convert Markdown to HTML using the library
    html_content = markdown.markdown(text)
    
    return f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f4; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            h1 {{ color: #0056b3; text-align: center; margin-bottom: 30px; font-size: 24px; }}
            h2 {{ color: #2c3e50; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; margin-top: 25px; font-size: 20px; }}
            h3 {{ color: #34495e; margin-top: 15px; margin-bottom: 5px; font-size: 18px; }}
            ul {{ padding-left: 20px; margin-bottom: 15px; }}
            li {{ margin-bottom: 10px; }}
            strong {{ color: #2c3e50; font-weight: 600; }}
            a {{ color: #0056b3; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #95a5a6; text-align: center; border-top: 1px solid #ecf0f1; padding-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Daily Tech Briefing</h1>
            <div class="content">
                {html_content}
            </div>
            <div class="footer">
                Generated by Perplexity Sonar Pro Agent • {datetime.now().strftime('%Y-%m-%d')}
            </div>
        </div>
    </body>
    </html>
    """

def send_email(summary):
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("⚠️ Email credentials missing.")
        return

    print("📧 Sending to Gmail...")
    try:
        msg = MIMEMultipart()
        msg['From'] = f"AI News Bot <{EMAIL_USER}>"
        msg['To'] = EMAIL_RECIPIENT
        msg['Subject'] = f"🚀 Tech Briefing - {datetime.now().strftime('%d %b %Y')}"

        html_content = markdown_to_html(summary)
        msg.attach(MIMEText(html_content, 'html'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, EMAIL_RECIPIENT, msg.as_string())
        server.quit()
        print("✅ Email Sent Successfully!")
    except Exception as e:
        print(f"❌ Email Error: {e}")

# --- Main ---
if __name__ == "__main__":
    updates = get_twitter_updates()
    if updates:
        summary = generate_summary(updates)
        if summary:
            send_email(summary)
        else:
            print("Failed to generate summary.")
    else:
        print("No recent tweets found today.")
