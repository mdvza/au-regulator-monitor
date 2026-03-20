"""
AU Regulator Monitor — e-commerce
Monitora ACCC e altri regulators australiani via Claude API con web search.
Invia un briefing settimanale via email.
"""

import anthropic
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ── Configurazione ──────────────────────────────────────────────
REGULATORS = ["ACCC", "OAIC", "Treasury Australia", "ACMA"]

QUERY = """
Sei un assistente legale specializzato in diritto della concorrenza e regolamentazione digitale australiana.

Prepara un briefing settimanale sugli aggiornamenti dei seguenti regulators australiani:
ACCC, OAIC, Treasury Australia, ACMA.

Focus specifico: piattaforme di e-commerce e marketplace online (es. eBay, Amazon, Catch, ecc.).

Per ciascun regulator, cerca e riporta:
1. Nuove enforcement actions o indagini avviate
2. Consultazioni aperte o chiuse di recente
3. Dichiarazioni pubbliche, discorsi o linee guida emesse
4. Aggiornamenti legislativi o reform proposals rilevanti
5. Decisioni o sentenze significative

Aree tematiche prioritarie:
- Unfair contract terms (UCT) e pratiche commerciali scorrette
- Digital Platform Services Inquiry (ACCC)
- Privacy reform e uso dei dati
- AI regulation e digital economy
- Consumer protection nel commercio online
- Misuse of market power (s 46 CCA)

Formato del report:
- Usa sezioni chiare per ciascun regulator
- Per ogni aggiornamento: titolo, data, breve sintesi (2-3 righe), rilevanza per piattaforme e-commerce
- Alla fine: una sezione "Action items" con eventuali scadenze o punti di attenzione

Periodo di ricerca: ultimi 7 giorni. Se non ci sono aggiornamenti recenti, segnalalo e includi gli aggiornamenti più recenti disponibili.
"""

# ── Funzione principale ──────────────────────────────────────────
def run_monitor():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Avvio monitoraggio regulators AU...")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Chiama Claude con web search abilitato
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": QUERY}]
    )

    # Estrai il testo dalla risposta
    report_text = ""
    for block in response.content:
        if block.type == "text":
            report_text += block.text

    if not report_text:
        report_text = "Nessun contenuto testuale trovato nella risposta. Verifica la configurazione."

    print("Report generato con successo.")
    print("─" * 60)
    print(report_text[:500] + "..." if len(report_text) > 500 else report_text)
    print("─" * 60)

    # Invia email
    send_email(report_text)

    return report_text


# ── Invio email ──────────────────────────────────────────────────
def send_email(report_text):
    sender = os.environ["EMAIL_SENDER"]
    recipient = os.environ["EMAIL_RECIPIENT"]
    password = os.environ["EMAIL_PASSWORD"]
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))

    today = datetime.now().strftime("%d %B %Y")
    subject = f"AU Regulator Monitor — Briefing settimanale {today}"

    # Versione HTML del report
    html_body = f"""
    <html><body style="font-family: Arial, sans-serif; max-width: 700px; margin: auto; color: #222;">
    <div style="background: #f4f4f4; padding: 20px 24px; border-radius: 8px; margin-bottom: 24px;">
        <h2 style="margin:0; color: #1a1a2e;">AU Regulator Monitor</h2>
        <p style="margin: 4px 0 0; color: #555; font-size: 14px;">Briefing settimanale — {today}</p>
        <p style="margin: 8px 0 0; color: #555; font-size: 13px;">
            Regulators: <strong>ACCC · OAIC · Treasury AU · ACMA</strong>
        </p>
    </div>
    <div style="white-space: pre-wrap; line-height: 1.7; font-size: 15px;">
{report_text}
    </div>
    <hr style="margin-top: 32px; border: none; border-top: 1px solid #ddd;">
    <p style="font-size: 12px; color: #999; margin-top: 12px;">
        Report generato automaticamente da AU Regulator Monitor · Claude API + web search<br>
        Per modificare le impostazioni, aggiorna il file <code>monitor.py</code> nel repository.
    </p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    msg.attach(MIMEText(report_text, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipient, msg.as_string())

    print(f"Email inviata a {recipient}")


if __name__ == "__main__":
    run_monitor()
