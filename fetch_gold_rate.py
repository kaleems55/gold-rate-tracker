import json
import re
import os
from datetime import date

from twilio.rest import Client
import os

import matplotlib.pyplot as plt

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

url = "https://www.goodreturns.in/gold-rates/"

DATA_FILE = "gold_rates.json"


options = Options()

options.add_argument("--headless=new")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")
options.add_argument("--window-size=1920,1080")
options.add_argument("--incognito")

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
    today = str(date.today())

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            data = json.load(f)
    else:
        data = []

    if not any(d["date"] == today for d in data):
        data.append({
            "date": today,
            "rate": rate
        })

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

    print("Today's rate saved:", rate)

    last10 = data[-10:]

    dates = [d["date"] for d in last10]
    rates = [d["rate"] for d in last10]

    plt.figure(figsize=(10,5))
    plt.plot(dates, rates, marker="o")
    plt.title("Gold Price Last 10 Days")
    plt.xlabel("Date")
    plt.ylabel("22K Price (INR)")
    plt.xticks(rotation=45)
    plt.grid(True)

    plt.tight_layout()

    plt.savefig("gold_price_chart.png")

    # ---------- SEND WHATSAPP MESSAGE ----------

    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")

    client = Client(account_sid, auth_token)

    chart_url = "https://raw.githubusercontent.com/kaleems55/gold-rate-tracker/main/gold_price_chart.png"

    message = client.messages.create(
        from_="whatsapp:+14155238886",
        to="whatsapp:+919500277388",
        body=f"Gold Rate Today: ₹{rate}/gram\n\n10-day trend chart:",
        media_url=[chart_url]
    )

finally:

    driver.quit()