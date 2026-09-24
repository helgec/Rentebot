import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Henter URL fra enten .env eller systemd-miljøet
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
TARGET_URL = "https://www.norges-bank.no/"

DATOER = {
    "2026-09-24", "2026-11-05", "2026-12-17",
    "2027-01-21", "2027-03-18", "2027-05-05", "2027-06-17", "2027-08-19"
}

def finn_styringsrente():
    url = "https://data.norges-bank.no/api/data/IR/B.KPRA.SD.R?format=csv&lastNObservations=1"
    try:
        response = requests.get(url, timeout=15)  # <--- Endret fra 5 til 15
        if response.status_code == 200:
            lines = [l.strip() for l in response.text.strip().splitlines() if l.strip()]
            if len(lines) >= 2:
                deler = [d.replace('"', '').strip() for d in lines[-1].split(';')]
                if len(deler) >= 9:
                    return {"dato": deler[7], "verdi": deler[8]}
    except Exception as e:
        print(f"❌ Feil ved henting: {e}")
    return None

def send_til_slack(melding):
    if not SLACK_WEBHOOK_URL:
        print("⚠️ Feil: Fant ingen SLACK_WEBHOOK_URL i miljøvariablene!")
        return
        
    try:
        requests.post(SLACK_WEBHOOK_URL, json={"text": melding})
    except Exception as e:
        print(f"❌ Feil ved sending til Slack: {e}")

def start_intensiv_overvaking():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starter intensiv overvåking...")
    
    baseline = finn_styringsrente()
    if not baseline:
        return

    last_date = baseline["dato"]
    last_rate = baseline["verdi"]
    
    start_time = time.time()
    
    while time.time() - start_time < 900:  # Kjører i 15 minutter
        data = finn_styringsrente()
        if data:
            ny_dato = data["dato"]
            ny_rente = data["verdi"]
            
            if ny_dato != last_date:
                uendret_tag = " (uendret)" if ny_rente == last_rate else ""
                melding = (
                    f"🏦 *NY RENTEBESLUTNING FRA NORGES BANK!* 💰\n\n"
                    f"```Styringsrente per {ny_dato}: {ny_rente}%{uendret_tag}```\n\n"
                    f"<{TARGET_URL}|Åpne Norges Bank>"
                )
                send_til_slack(melding)
                return 
                
        time.sleep(3)

def monitor_loop():
    print("🤖 Rentebot kjører i bakgrunnen...")
    while True:
        naa = datetime.now()
        dagens_dato = naa.strftime("%Y-%m-%d")
        
        if dagens_dato in DATOER and naa.hour == 9 and naa.minute == 59:
            start_intensiv_overvaking()
            time.sleep(180) 
        else:
            time.sleep(10)

if __name__ == "__main__":
    monitor_loop()
