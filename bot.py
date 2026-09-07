import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# Laster inn miljøvariabler
load_dotenv()

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL")
TARGET_URL = "https://www.norges-bank.no/"

# Datoene rentebeslutningene offentliggjøres (Format: YYYY-MM-DD)
DATOER = {
    "2026-09-24", "2026-11-05", "2026-12-17",
    "2027-01-21", "2027-03-18", "2027-05-05", "2027-06-17", "2027-08-19"
}

def finn_styringsrente():
    """Henter nyeste styringsrente fra Norges Banks API."""
    url = "https://data.norges-bank.no/api/data/IR/B.KPRA.SD.R?format=csv&lastNObservations=1"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            lines = response.text.strip().splitlines()
            if len(lines) >= 2:
                data = lines[-1].split(";")
                # Henter dato (indeks 8) og verdi (indeks 10)
                dato = data[8].replace('"', '').strip()
                rente_verdi = data[10].replace('"', '').strip()
                return {"dato": dato, "verdi": rente_verdi}
    except Exception as e:
        print(f"❌ Feil ved henting: {e}")
    return None

def send_til_slack(melding):
    """Sender melding til Slack via Webhook."""
    if not SLACK_WEBHOOK_URL:
        print("⚠️ Feil: Mangler SLACK_WEBHOOK_URL i .env-filen!")
        return
        
    payload = {"text": melding}
    try:
        requests.post(SLACK_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"❌ Feil ved sending til Slack: {e}")

def start_intensiv_overvaking():
    """Kjører hvert 3. sekund mellom 09:59 og 10:01."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starter intensiv overvåking...")
    
    # Finn utgangspunktet (baselinen) før kunngjøringen
    baseline = finn_styringsrente()
    if not baseline:
        print("⚠️ Klarte ikke hente opprinnelig rente. Prøver igjen senere.")
        return

    last_date = baseline["dato"]
    last_rate = baseline["verdi"]
    
    start_time = time.time()
    VARIGHET_SEKUNDER = 120  # 2 minutter
    
    while time.time() - start_time < VARIGHET_SEKUNDER:
        data = finn_styringsrente()
        if data:
            ny_dato = data["dato"]
            ny_rente = data["verdi"]
            
            # API-et oppdateres med Dagens Dato når ny rente publiseres
            if ny_dato != last_date:
                uendret_tag = " (uendret)" if ny_rente == last_rate else ""
                melding = (
                    f"📢 *NY RENTEBESLUTNING FRA NORGES BANK!* 📢\n\n"
                    f"```Styringsrente per {ny_dato}: {ny_rente}%{uendret_tag}```\n\n"
                    f"<{TARGET_URL}|Åpne Norges Bank>"
                )
                
                send_til_slack(melding)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Endring funnet og postet til Slack!")
                
                # Siden vi fant endringen, avslutter vi overvåkingen for i dag
                return 
                
        # Sjekk hvert 3. sekund
        time.sleep(3)
        
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 2 minutter gikk uten oppdatering fra Norges Bank.")

def monitor_loop():
    """Hovedløkke som står og lytter etter riktig dato og klokkeslett."""
    print("🤖 Rentebot kjører i bakgrunnen og venter på neste rentebeslutning...")
    
    while True:
        naa = datetime.now()
        dagens_dato = naa.strftime("%Y-%m-%d")
        
        # Sjekker om det er riktig dato, time og minutt
        if dagens_dato in DATOER and naa.hour == 9 and naa.minute == 59:
            start_intensiv_overvaking()
            
            # Sov i 3 minutter etterpå, så vi unngår at klokka fortsatt
            # er 09:59 og trigger intensiv overvåking en gang til
            time.sleep(180) 
        else:
            # Sov i 10 sekunder før vi sjekker klokka på nytt
            time.sleep(10)

if __name__ == "__main__":
    monitor_loop()
