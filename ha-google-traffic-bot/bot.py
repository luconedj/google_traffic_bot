import os
import re
import threading
import time
import urllib.parse
from datetime import datetime
import requests
from playwright.sync_api import sync_playwright
import schedule

# ================= CONFIGURAZIONE DA AMBIENTE (HA ADD-ON) =================
ORIGIN = os.getenv("ORIGIN", "")
DESTINATION = os.getenv("DESTINATION", "")

CHECK_INTERVAL_MINUTES = int(os.getenv("CHECK_INTERVAL_MINUTES", "10"))
DIFF_THRESHOLD_MINUTES = int(os.getenv("DIFF_THRESHOLD_MINUTES", "5"))
FREE_TRAFFIC_THRESHOLD_MINUTES = int(os.getenv("FREE_TRAFFIC_THRESHOLD_MINUTES", "35"))

# Gestione flag Telegram (convertito in booleano da stringa)
ENABLE_TELEGRAM = os.getenv("ENABLE_TELEGRAM", "false").lower() in ("true", "1", "yes", "on")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
SUPERVISOR_TOKEN = os.getenv("SUPERVISOR_TOKEN", "")
# =========================================================================

is_running = True
last_checked_duration = None
last_duration = None
global_page = None


def send_telegram_notification(message):
  # Se Telegram non è abilitato o mancano le credenziali, esce senza fare nulla
  if not ENABLE_TELEGRAM or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    return

  url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
  try:
    response = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=5)
    if not response.ok:
      print(f"Errore invio Telegram: {response.text}")
  except Exception as e:
    print(f"Errore di connessione a Telegram: {e}")


def update_ha_sensor(duration, status_active):
  if not SUPERVISOR_TOKEN:
    print("[HA API] SUPERVISOR_TOKEN non trovato. Aggiornamento HA saltato.")
    return

  url = "http://supervisor/core/api/states/sensor.traffico_napoli_caserta"
  headers = {
      "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
      "Content-Type": "application/json",
  }

  payload = {
      "state": duration if duration is not None else "unavailable",
      "attributes": {
          "unit_of_measurement": "min",
          "friendly_name": "Tratta Monitorata (Traffico)",
          "icon": "mdi:car-clock",
          "bot_status": "Attivo" if status_active else "Pausa",
          "origin": ORIGIN,
          "destination": DESTINATION,
      },
  }

  try:
    response = requests.post(url, json=payload, headers=headers, timeout=5)
    if not response.ok:
      print(f"[HA API] Errore aggiornamento sensore: {response.status_code}")
  except Exception as e:
    print(f"[HA API] Eccezione di rete verso Home Assistant: {e}")


def telegram_listener_thread():
  global is_running, last_checked_duration
  
  if not ENABLE_TELEGRAM:
    print("🤖 [THREAD] Listener Telegram disabilitato da configurazione.")
    return

  last_update_id = 0
  print("🤖 [THREAD] Listener Telegram ultra-rapido avviato in background.")

  while ENABLE_TELEGRAM:
    try:
      url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={last_update_id}&timeout=1"
      response = requests.get(url, timeout=3)

      if response.ok:
        data = response.json()
        for result in data.get("result", []):
          last_update_id = result["update_id"] + 1
          message = result.get("message", {})
          chat_id = str(message.get("chat", {}).get("id"))

          if chat_id != str(TELEGRAM_CHAT_ID):
            continue

          text = message.get("text", "").strip().lower()
          print(f"[TELEGRAM] Comando ricevuto: '{text}'")

          if text in ["/avvia", "/start"]:
            if not is_running:
              is_running = True
              send_telegram_notification("▶️ **Bot riavviato!** Il monitoraggio del traffico è ora attivo.")
              update_ha_sensor(last_checked_duration, is_running)
            else:
              send_telegram_notification("ℹ️ Il bot è **già attivo** e in esecuzione.")

          elif text in ["/ferma", "/stop"]:
            if is_running:
              is_running = False
              send_telegram_notification("⏸️ **Bot messo in pausa!** Il monitoraggio è stato fermato.")
              update_ha_sensor(last_checked_duration, is_running)
            else:
              send_telegram_notification("ℹ️ Il bot è **già in pausa**.")

          elif text == "/stato":
            status_msg = (
                f"📊 **Stato Bot Traffico**\n"
                f"- Stato: {'🟢 Attivo' if is_running else '⏸️ In pausa'}\n"
                f"- Ultimo tempo: {last_checked_duration if last_checked_duration else 'N/D'} min"
            )
            send_telegram_notification(status_msg)

    except Exception:
      pass

    time.sleep(2)


def clean_text(text):
  if not text:
    return ""
  cleaned = "".join(c for c in text if not (0xE000 <= ord(c) <= 0xF8FF))
  return cleaned.strip()


def parse_duration_to_minutes(text):
  cleaned_text = clean_text(text)
  if not cleaned_text:
    return None

  total_minutes = 0
  hours_match = re.search(r"(\d+)\s*(?:ora|ore|h)", cleaned_text, re.IGNORECASE)
  if hours_match:
    total_minutes += int(hours_match.group(1)) * 60

  mins_match = re.search(r"(\d+)\s*(?:min|m)", cleaned_text, re.IGNORECASE)
  if mins_match:
    total_minutes += int(mins_match.group(1))

  return total_minutes if total_minutes > 0 else None


def get_traffic_duration(page):
  if not ORIGIN or not DESTINATION:
    print("[ERRORE] Indirizzo di partenza o arrivo non configurati in Home Assistant!")
    return None

  encoded_origin = urllib.parse.quote(ORIGIN)
  encoded_dest = urllib.parse.quote(DESTINATION)
  url = f"https://www.google.com/maps/dir/{encoded_origin}/{encoded_dest}"

  print(f"[{datetime.now().strftime('%H:%M:%S')}] Apertura Google Maps in corso...")
  try:
    page.goto(url, timeout=60000)
  except Exception as e:
    print(f"Errore di navigazione Playwright: {e}")
    return None

  try:
    for selector in [
        "button[aria-label='Accetta tutto']",
        "button:has-text('Accetta tutto')",
        "button:has-text('Accept all')",
        "form[action*='consent'] button",
    ]:
      btn = page.locator(selector).first
      if btn.is_visible(timeout=2000):
        btn.click()
        print("Banner cookie chiuso con successo.")
        time.sleep(2)
        break
  except Exception:
    pass

  try:
    page.wait_for_selector("div.ivN21e, div.tUEPjf, div[data-trip-index]", timeout=15000)

    duration_elements = page.locator(
        "div[data-trip-index] div.Fk3nvb, div.ivN21e, div.tUEPjf, span[jsan*='7.fontHeadlineLarge']"
    ).all_inner_texts()

    if not duration_elements:
      duration_elements = page.locator("span:has-text('min'), div:has-text('min')").all_inner_texts()

    for text in duration_elements:
      cleaned = clean_text(text)
      if (
          len(cleaned) < 25
          and ("min" in cleaned.lower() or "h" in cleaned.lower())
          and "partenza" not in cleaned.lower()
          and "arrivo" not in cleaned.lower()
      ):
        mins = parse_duration_to_minutes(cleaned)
        if mins:
          print(f"Tempo rilevato con successo: '{cleaned}' -> {mins} minuti")
          return mins

    time_text = page.evaluate(
        """() => {
            const elements = Array.from(document.querySelectorAll('div, span'));
            const match = elements.find(el => el.innerText && (el.innerText.includes('min') || el.innerText.includes('ora')) && el.innerText.length < 15 && !el.innerText.includes('partenza'));
            return match ? match.innerText : null;
        }"""
    )
    if time_text:
      cleaned_js = clean_text(time_text)
      mins = parse_duration_to_minutes(cleaned_js)
      if mins:
        print(f"Tempo rilevato via JS fallback: '{cleaned_js}' -> {mins} minuti")
        return mins

  except Exception as e:
    print(f"Errore durante il recupero dei dati da Google Maps: {e}")

  return None


def job_check_traffic():
  global is_running, last_checked_duration, last_duration, global_page

  if not is_running:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Bot in pausa. Controllo traffico saltato.")
    return

  current_time = datetime.now().strftime("%H:%M")
  current_duration = get_traffic_duration(global_page)

  if current_duration is not None:
    last_checked_duration = current_duration
    print(f"[{current_time}] Durata attuale stimata: {current_duration} min")

    update_ha_sensor(current_duration, is_running)

    if last_duration is not None:
      diff = current_duration - last_duration

      if abs(diff) >= DIFF_THRESHOLD_MINUTES:
        direction = "aumentato" if diff > 0 else "diminuito"
        msg = (
            f"⚠️ Attenzione! Il traffico è {direction} di {abs(diff)} min.\n"
            f"🕒 Tempo attuale: {current_duration} min (precedente: {last_duration} min)."
        )
        send_telegram_notification(msg)
      elif (
          current_duration <= FREE_TRAFFIC_THRESHOLD_MINUTES
          and last_duration > FREE_TRAFFIC_THRESHOLD_MINUTES
      ):
        msg = (
            f"🟢 Percorso libero! Il tempo di percorrenza è sceso a {current_duration} min."
        )
        send_telegram_notification(msg)
    else:
      send_telegram_notification(
          f"🤖 Bot Add-on avviato. Monitoraggio attivo. Tempo iniziale: {current_duration} min."
      )

    last_duration = current_duration
  else:
    print(f"[{current_time}] Impossibile leggere il tempo di traffico.")

  print(f"Prossimo controllo pianificato tra {CHECK_INTERVAL_MINUTES} minuti.\n")


def main():
  global global_page
  print(f"--- Avvio Google Maps Traffic Bot (HA Local Add-on) ---")
  print(f"Partenza: {ORIGIN if ORIGIN else '[Non configurata]'}")
  print(f"Arrivo:   {DESTINATION if DESTINATION else '[Non configurata]'}")
  print(f"Intervallo: {CHECK_INTERVAL_MINUTES} minuti")
  print(f"Telegram abilitato: {ENABLE_TELEGRAM}\n")

  send_telegram_notification("🤖 **Bot Traffico Add-on avviato in Home Assistant!**")

  t = threading.Thread(target=telegram_listener_thread, daemon=True)
  t.start()

  with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-dev-shm-usage",
        ],
    )

    context = browser.new_context(
        locale="it-IT",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1280, "height": 800},
    )

    global_page = context.new_page()

    job_check_traffic()
    schedule.every(CHECK_INTERVAL_MINUTES).minutes.do(job_check_traffic)

    try:
      while True:
        schedule.run_pending()
        time.sleep(1)
    except KeyboardInterrupt:
      print("\nMonitoraggio interrotto.")
    finally:
      browser.close()


if __name__ == "__main__":
  main()
