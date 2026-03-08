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

try:

    driver.get(url)

    WebDriverWait(driver, 30).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )

    page_text = driver.find_element("tag name", "body").text

    match = re.search(r'₹\s?([\d,]+)\s*per\s*gram\s*for\s*22\s*karat', page_text, re.IGNORECASE)

    if not match:
        raise Exception("Gold rate not found")

    rate = int(match.group(1).replace(",", ""))

    print("Today's rate saved:", rate)

finally:
    driver.quit()


# -----------------------------
# LOAD HISTORY
# -----------------------------

if os.path.exists(file_path):

    with open(file_path, "r") as f:
        history = json.load(f)

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

with open(file_path, "w") as f:
    json.dump(history, f, indent=4)


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

plt.figure(figsize=(8,4))
plt.plot(dates, prices, marker="o")
plt.title("Gold Price (Last 10 Days)")
plt.xlabel("Date")
plt.ylabel("Price ₹/g")
plt.xticks(rotation=45)
plt.tight_layout()

os.makedirs("docs", exist_ok=True)
plt.savefig(chart_path)
plt.close()

print("Chart generated")


# -----------------------------
# WEEKLY PRICE ALERT
# -----------------------------

alert_text = ""

if len(history) >= 7:

    price_today = history[-1]["gold_rate_22k"]
    price_week_ago = history[-7]["gold_rate_22k"]

    weekly_change = price_today - price_week_ago

    if weekly_change < 0:
        alert_text = f"Alert: price dropped ₹{abs(weekly_change)} this week"

    elif weekly_change > 0:
        alert_text = f"Alert: price increased ₹{weekly_change} this week"

    else:
        alert_text = "Price unchanged this week"


# -----------------------------
# SEND WHATSAPP MESSAGE
# -----------------------------

account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

if account_sid and auth_token:

    try:

        client = Client(account_sid, auth_token)

        message = client.messages.create(

            from_="whatsapp:+14155238886",
            to="whatsapp:+919500277388",   # replace with your number

            body=f"""
Gold Rate Today: ₹{rate}/gram

{alert_text}

10-day trend chart attached.
""",

            media_url=[chart_url]

        )

        print("WhatsApp message sent")

    except Exception as e:
        print("Twilio error:", e)