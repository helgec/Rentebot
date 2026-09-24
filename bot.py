import os
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
TARGET_URL = "https://www.norges-bank.no/"

DATOER = {
    "2026-09-24", "2026-11-05", "2026-12-17",
    "2027-01-21", "2027-03-18", "2027-05-05", "2027-06-17", "2027-08-19"
}

def finn_siste_pressemelding():
    """Henter nyeste pressemelding fra Norges Banks RSS-feed."""
    url = "https://www.norges-bank.no/rss/Pressemeldinger/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            items = root.findall("./channel/item")
            for item in items:
                title_elem = item.find("title")
                link_elem = item.find("link")
                
                tittel = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                lenke = link_elem.text.strip() if link_elem is not None and link_elem.text else TARGET_URL
                
                # Sjekker at saken handler om rente
                if "rente" in tittel.lower():
                    return {"tittel": tittel, "lenke": lenke}
    except Exception as e:
        print(f"❌ Feil ved henting av RSS: {e}")
    return None

def send_til_slack(melding):
    if not SLACK_WEBHOOK_URL:
        print("⚠️ Feil: Fant ingen SLACK_WEBHOOK_URL!")
        return
    try:
        requests.post(SLACK_WEBHOOK_URL, json={"text": melding})
    except Exception as e:
        print(f"❌ Feil ved sending til Slack: {e}")

def start_intensiv_overvaking():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starter intensiv sanntidsovervåking av pressemeldinger...")
    
    baseline = finn_siste_pressemelding()
    siste_tittel = baseline["tittel"] if baseline else ""
    
    start_time = time.time()
    
    # Sjekker hvert 2. sekund i opptil 10 minutter
    while time.time() - start_time < 600:
        sak = finn_siste_pressemelding()
        if sak:
            ny_tittel = sak["tittel"]
            lenke = sak["lenke"]
            
            # Utløses i samme sekund som en ny overskrift legges ut
            if ny_tittel != siste_tittel:
                melding = (
                    f"🏦 *NY RENTEBESLUTNING FRA NORGES BANK!* 💰\n\n"
                    f"```{ny_tittel}```\n\n"
                    f"<{lenke}|Les pressemeldingen hos Norges Bank>"
                )
                send_til_slack(melding)
                print(f"✅ Ny rentebeslutning sendt til Slack: {ny_tittel}")
                return 
                
        time.sleep(2)

    print("⚠️ Overvåking fullført etter 10 minutter uten ny pressemelding.")

def monitor_loop():
    print("🤖 Rentebot kjører i bakgrunnen (sanntidsovervåking)...")
    while True:
        naa = datetime.now()
        dagens_dato = naa.strftime("%Y-%m-%d")
        
        if dagens_dato in DATOER and naa.hour == 9 and naa.minute == 59:
            start_intensiv_overvaking()
            time.sleep(180) 
        else:
            time.sleep(5)

if __name__ == "__main__":
    monitor_loop()
