import os
import time
import requests
import feedparser
import smtplib
import re
import html
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from time import mktime
from google import genai

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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip().replace('"', '')
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

# --- 3. Generate Summary (Google Gemini) ---
def generate_summary(tweets_text):
    if not tweets_text: return None

    print("Generating Smart Digest (Google Gemini)...")

    prompt = f"""
    You are a Tech Intelligence Agent. Here are the latest tweets from key tech accounts collected over the last 24 hours:
    
    {tweets_text}
    
    INSTRUCTIONS:
    1. Analyze these tweets.
    2. Verify facts if tweets are vague.
    3. Create a **"Daily Tech Briefing"**.
    4. Group updates logically (AI, Space, Big Tech).
    5. Write concise, engaging summaries with Emojis.
    
    IMPORTANT: Do not use Markdown tables. Use bullet points.
    """

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        return response.text
    except Exception as e:
        print(f"AI Error: {e}")
        return None

# --- 4. Send Email ---
def markdown_to_html(text):
    if not text: return ""
    # Basic Markdown to HTML conversion
    text = html.escape(text)
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text) # Bold
    text = text.replace('\n', '<br>')
    
    return f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; background-color: #f4f4f4; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1);">
            <h2 style="color: #0056b3; text-align: center; border-bottom: 2px solid #eee; padding-bottom: 10px;">🚀 Daily Tech Briefing</h2>
            <div style="font-size: 14px;">
                {text}
            </div>
            <br><hr style="border: 0; border-top: 1px solid #eee;">
            <p style="font-size: 12px; color: #777; text-align: center;">Generated by Google Gemini Agent</p>
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
