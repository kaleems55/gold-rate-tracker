import json
import os
import re
from datetime import date
import matplotlib.pyplot as plt

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from twilio.rest import Client


# -----------------------------
# CONFIG
# -----------------------------

url = "https://www.goodreturns.in/gold-rates/"
file_path = "gold_rates.json"
chart_path = "docs/gold_price_chart.png"

# public chart URL (used by Twilio)
chart_url = "https://raw.githubusercontent.com/kaleems55/gold-rate-tracker/main/docs/gold_price_chart.png"


# -----------------------------
# FETCH GOLD RATE
# -----------------------------

options = Options()
options.add_argument("--headless=new")
options.add_argument("--incognito")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=options)
rate = None

try:
    driver.get(url)

    WebDriverWait(driver, 30).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )

    page_text = driver.find_element("tag name", "body").text

    match = re.search(r'₹\s?([\d,]+)\s*per\s*gram\s*for\s*22\s*karat', page_text, re.IGNORECASE)

    if not match:
        raise Exception("Gold rate not found on page")

    rate = int(match.group(1).replace(",", ""))

    print("Today's rate saved:", rate)

except Exception as e:
    print(f"Scraping error: {e}")
    driver.quit()
    exit(1)  # Exit early if scraping fails

finally:
    driver.quit()


# -----------------------------
# LOAD HISTORY
# -----------------------------

if os.path.exists(file_path):
    try:
        with open(file_path, "r") as f:
            history = json.load(f)
    except json.JSONDecodeError:
        print("Warning: corrupted JSON file, starting fresh")
        history = []
else:
    history = []


# -----------------------------
# APPEND TODAY PRICE
# -----------------------------

today = str(date.today())

today_data = {
    "date": today,
    "gold_rate_22k": rate
}

if history and history[-1]["date"] == today:
    history[-1]["gold_rate_22k"] = rate
else:
    history.append(today_data)


# -----------------------------
# SAVE JSON
# -----------------------------

try:
    with open(file_path, "w") as f:
        json.dump(history, f, indent=4)
    print("History saved")
except Exception as e:
    print(f"Error saving history: {e}")


# -----------------------------
# GENERATE CHART (LAST 10 DAYS)
# -----------------------------

recent = history[-10:]

dates = []
prices = []

for item in recent:
    if "gold_rate_22k" in item:
        dates.append(item["date"])
        prices.append(item["gold_rate_22k"])

try:
    os.makedirs("docs", exist_ok=True)
    
    plt.figure(figsize=(8, 4))
    plt.plot(dates, prices, marker="o", linewidth=2, color="gold")
    plt.title("Gold Price (Last 10 Days)", fontsize=14, fontweight="bold")
    plt.xlabel("Date")
    plt.ylabel("Price ₹/gram")
    plt.xticks(rotation=45)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    plt.savefig(chart_path, dpi=100)
    plt.close()
    
    print("Chart generated successfully")
except Exception as e:
    print(f"Chart generation error: {e}")


# -----------------------------
# WEEKLY PRICE ALERT
# -----------------------------

alert_text = "📊 Not enough data yet (need 7 days)"

if len(history) >= 7:
    price_today = history[-1]["gold_rate_22k"]
    price_week_ago = history[-7]["gold_rate_22k"]

    weekly_change = price_today - price_week_ago

    if weekly_change < 0:
        alert_text = f"📉 Alert: price dropped ₹{abs(weekly_change)} this week"

    elif weekly_change > 0:
        alert_text = f"📈 Alert: price increased ₹{weekly_change} this week"

    else:
        alert_text = "➡️ Price unchanged this week"

print(f"Alert text: {alert_text}")  # Debug line


# -----------------------------
# SEND WHATSAPP MESSAGE
# -----------------------------

account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
# Multiple recipients
recipients = [
    os.environ.get("WHATSAPP_TO_1", "whatsapp:+919500277388"),
    os.environ.get("WHATSAPP_TO_2", "whatsapp:+917358240495"),
]

if account_sid and auth_token:
    try:
        client = Client(account_sid, auth_token)

        for to_number in recipients:
            message = client.messages.create(
                from_="whatsapp:+14155238886",
                to=to_number,
                body=f"""
Gold Rate Today: ₹{rate}/gram

{alert_text}

10-day trend chart attached.
""",
                media_url=[chart_url]
            )
            print(f"WhatsApp message sent to {to_number}")

    except Exception as e:
        print(f"Twilio error: {e}")
else:
    print("Warning: Twilio credentials not found. Skipping WhatsApp alert.")