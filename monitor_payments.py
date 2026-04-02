"""
AU Payments & Financial Services Monitor
Monitors RBA, ASIC, AUSTRAC, FATF, APRA, AFCA, OAIC, Treasury AU, ACMA
via Claude API with web search.
Sends a weekly briefing email to the payments legal team.
"""

import anthropic
import smtplib
import os
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ── Regulator sources to scrape ──────────────────────────────────
REGULATOR_SOURCES = [
    {"name": "RBA", "url": "https://www.rba.gov.au/media-releases/", "selector": "h3, h2, a"},
    {"name": "ASIC", "url": "https://asic.gov.au/about-asic/news-centre/find-a-media-release/", "selector": "h3, h2"},
    {"name": "AUSTRAC", "url": "https://www.austrac.gov.au/news-and-media", "selector": "h3, h2"},
    {"name": "APRA", "url": "https://www.apra.gov.au/news-and-publications", "selector": "h3, h2"},
    {"name": "FATF", "url": "https://www.fatf-gafi.org/en/topics/fatf-recommendations.html", "selector": "h3, h2"},
    {"name": "AFCA", "url": "https://www.afca.org.au/news", "selector": "h3, h2"},
    {"name": "OAIC", "url": "https://www.oaic.gov.au/updates/news-and-media", "selector": "h3, h2"},
    {"name": "Treasury", "url": "https://treasury.gov.au/consultation", "selector": "h3, h2"},
    {"name": "ACMA", "url": "https://www.acma.gov.au/newsroom", "selector": "h3, h2"},
]

# ── Scrape regulator sites ───────────────────────────────────────
def scrape_sources():
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    results = []
    for source in REGULATOR_SOURCES:
        try:
            resp = requests.get(source["url"], headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                items = soup.select(source["selector"])
                titles = [item.get_text(strip=True) for item in items[:10] if len(item.get_text(strip=True)) > 20]
                if titles:
                    results.append("**" + source["name"] + "** (" + source["url"] + "):\n" + "\n".join("- " + t for t in titles[:8]))
                else:
                    results.append("**" + source["name"] + "**: No recent content found.")
            else:
                results.append("**" + source["name"] + "**: Could not access site (status " + str(resp.status_code) + ").")
        except Exception as e:
            results.append("**" + source["name"] + "**: Error accessing site (" + str(e)[:60] + ").")
    return "\n\n".join(results)


# ── Main query ───────────────────────────────────────────────────
def build_query(scraped_content):
    today = datetime.now().strftime("%d %B %Y")
    prompt = """You are a senior legal counsel specialising in Australian financial services law, payments regulation, AML/CTF compliance, privacy, and prudential regulation.

Today is """ + today + """. Prepare a professional weekly briefing on regulatory developments in Australia relevant to payments, financial services, and AML/CTF compliance — with specific focus on entities holding an Australian Financial Services Licence (AFSL).

IMPORTANT INSTRUCTIONS:
- Write entirely in clear, plain English. No other languages.
- Be concise and professional. Each update should be 2-4 sentences maximum.
- Use the exact structure below. Do not deviate from it.
- Your response MUST start with the exact text: EXECUTIVE SUMMARY (on its own line).
- Never write introductory sentences before EXECUTIVE SUMMARY.
- Never combine section headers with other text on the same line.
- Do not include ANY preamble, meta-commentary, or explanation of what you are doing.
- For EVERY update, include the exact URL of the specific page found during web search: [Read more](https://exact-url.com)
- The URL must point to the specific article or press release — NOT a homepage or index page.
- Prefer official sources: regulator websites, government legislation pages, FATF publications.

---

STRUCTURE TO FOLLOW:

EXECUTIVE SUMMARY
[2-3 sentences summarising the most important developments this week and their significance for AFSL holders and payments businesses.]

---

1. RBA (Reserve Bank of Australia)

For each update:
• **[Title]** — [Date if known]
[2-3 sentence summary and relevance for payments/AFSL holders.] [Read more](https://exact-url.com)

Search for: payments system regulation, payment standards, digital currency, crypto-asset developments, consultations on payment infrastructure.

---

2. ASIC (Australian Securities and Investments Commission)

Same format. Search for: enforcement actions against financial services companies, AFSL guidance and licensing changes, directors duties, company reporting obligations and ASIC portal changes, crypto-asset regulation, consumer protection in financial services.

---

3. AUSTRAC (Australian Transaction Reports and Analysis Centre)

Same format. Search for: AML/CTF rule changes, enforcement actions and penalties, suspicious matter reporting (SMR) obligations, designated services updates, fintech and digital currency guidance, high-risk jurisdiction guidance.

---

4. APRA (Australian Prudential Regulation Authority)

Same format. Search for: prudential standards updates, enforcement actions, ADI guidance, capital and liquidity requirements, superannuation regulation updates.

---

5. FATF (Financial Action Task Force)

Same format. Search for: changes to blacklists and greylists — list specific countries added or removed, new FATF recommendations or typologies, mutual evaluation reports relevant to Australia, virtual asset and VASP regulation, FATF statements relevant to Australian AML/CTF obligations.

---

6. AFCA (Australian Financial Complaints Authority)

Same format. Search for: significant determinations relevant to payments and financial services, industry guidance and rule changes, systemic issue investigations, operational updates.

---

7. OAIC (Office of the Australian Information Commissioner)

Same format. Search for: Privacy Act reform updates relevant to financial services, enforcement actions against financial or payments companies, guidance on data handling and AI, notifiable data breach trends.

---

8. TREASURY AUSTRALIA

Same format. Search for: financial services reform proposals, payments system reform and licensing, BNPL regulation updates, digital assets and crypto regulation, CDR (Consumer Data Right) updates affecting financial services.

---

9. ACMA (Australian Communications and Media Authority)

Same format. Search for: scam and fraud enforcement relevant to financial services and payments, SMS and communications regulation affecting financial institutions, scam awareness industry obligations.

---

10. LAW FIRM INSIGHTS
[Summarise any content from the scraped sources below that is relevant to payments, financial services, AML/CTF, privacy, or AFSL holders. State source name, topic, 1-2 sentence summary, and link if available.]

Scraped content from regulator sites today:
""" + (scraped_content if scraped_content else "No content available this week.") + """

---

ACTION ITEMS
[Bullet list of concrete actions or deadlines for a payments legal team or AFSL holder in the next 30-60 days. Include: consultation deadlines, reporting obligations, ASIC portal changes, FATF greylist/blacklist changes, procedural updates for directors. Be specific with dates where known.]

---

If there are no updates for a section this week, write: "No significant updates this week."
Do not fabricate or speculate. Only report what you find through web search."""
    return prompt


# ── Main function ────────────────────────────────────────────────
def run_monitor():
    print("[" + datetime.now().strftime("%Y-%m-%d %H:%M") + "] Starting AU Payments & Financial Services Monitor...")
    print("Scraping regulator websites...")
    scraped_content = scrape_sources()
    print("Scraping complete.")
    print("Calling Claude API with web search...")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": build_query(scraped_content)}]
    )
    report_text = ""
    for block in response.content:
        if block.type == "text":
            report_text += block.text
    if not report_text:
        report_text = "Error: No report content generated. Please check the API configuration."
    print("Report generated successfully.")
    print("─" * 60)
    print(report_text[:300] + "...")
    print("─" * 60)
    send_email(report_text)
    return report_text


# ── Section colour map ───────────────────────────────────────────
SECTION_COLORS = {
    "rba":          {"bg": "#EBF4FF", "border": "#2B7FD4"},
    "asic":         {"bg": "#EDF7F2", "border": "#2BA876"},
    "austrac":      {"bg": "#FFF8EB", "border": "#D4902B"},
    "apra":         {"bg": "#F3EEFF", "border": "#7B5EA7"},
    "fatf":         {"bg": "#FFF0F0", "border": "#D45A5A"},
    "afca":         {"bg": "#F0FFF4", "border": "#2BAA5A"},
    "oaic":         {"bg": "#E8F4F8", "border": "#2B9BD4"},
    "treasury":     {"bg": "#FFFBEB", "border": "#C4820B"},
    "acma":         {"bg": "#F5F0FF", "border": "#6B5EA7"},
    "law firm":     {"bg": "#F0F6FF", "border": "#5A8AD4"},
    "action items": {"bg": "#F0F9FF", "border": "#2BB5D4"},
    "executive":    {"bg": "#F8F8F8", "border": "#AAAAAA"},
}

def get_section_color(title):
    t = title.lower()
    for key, val in SECTION_COLORS.items():
        if key in t:
            return val
    return {"bg": "#F4F6F8", "border": "#AAAAAA"}

def render_html(report_text, today):
    import re
    lines = report_text.split("\n")

    def apply_inline(text):
        text = re.sub(
            r'\[([^\]]+)\]\((https?://[^\)]+)\)',
            r'<a href="\2" style="color:#2B7FD4;text-decoration:none;font-weight:600;">\1 \u2197</a>',
            text
        )
        parts = text.split("**")
        result = ""
        for i, part in enumerate(parts):
            result += "<strong>" + part + "</strong>" if i % 2 == 1 else part
        return result

    def render_line(stripped):
        if not stripped or stripped == "---":
            return ""
        if stripped.startswith("\u2022 ") or stripped.startswith("- "):
            return '<p style="margin:5px 0 5px 12px;color:#333;font-size:14px;line-height:1.65;">&#8226;&nbsp;' + apply_inline(stripped[2:]) + "</p>"
        if stripped.startswith("**") and "**" in stripped[2:]:
            end = stripped.index("**", 2)
            title_text = stripped[2:end]
            rest = stripped[end+2:].strip(" \u2014-")
            date_html = '<span style="color:#888;font-size:12px;margin-left:8px;">' + rest + "</span>" if rest else ""
            return '<p style="margin:14px 0 4px;font-size:14px;font-weight:700;color:#1a1a2e;">' + title_text + date_html + "</p>"
        return '<p style="margin:5px 0;color:#444;font-size:14px;line-height:1.7;">' + apply_inline(stripped) + "</p>"

    header_split = re.compile(
        r'(EXECUTIVE SUMMARY|ACTION ITEMS|\d+\.\s+(?:RBA|ASIC|AUSTRAC|APRA|FATF|AFCA|OAIC|TREASURY|ACMA|LAW FIRM)[^\n]*)',
        re.IGNORECASE
    )
    processed = []
    for line in lines:
        parts = header_split.split(line)
        if len(parts) > 1:
            for part in parts:
                if part.strip():
                    processed.append(part.strip())
        else:
            processed.append(line)

    section_pattern = re.compile(
        r'^(EXECUTIVE SUMMARY|ACTION ITEMS|\d+\.\s+(RBA|ASIC|AUSTRAC|APRA|FATF|AFCA|OAIC|TREASURY|ACMA|LAW FIRM))',
        re.IGNORECASE
    )

    html_sections = []
    cur_title = None
    cur_color = None
    cur_lines_html = []

    for line in processed:
        stripped = line.strip()
        if not stripped or stripped == "---":
            continue
        m = section_pattern.match(stripped)
        if m:
            if cur_title:
                inner = "".join(cur_lines_html)
                c = cur_color
                html_sections.append(
                    '<div style="margin-bottom:20px;border-radius:8px;overflow:hidden;border:1.5px solid ' + c["border"] + ';"><div style="background:' + c["border"] + ';padding:9px 18px;"><span style="color:#fff;font-size:12px;font-weight:700;letter-spacing:0.09em;text-transform:uppercase;">' + cur_title + '</span></div><div style="background:' + c["bg"] + ';padding:16px 18px 12px;">' + inner + '</div></div>'
                )
            cur_title = stripped
            cur_color = get_section_color(stripped)
            cur_lines_html = []
        else:
            cur_lines_html.append(render_line(stripped))

    if cur_title:
        inner = "".join(cur_lines_html)
        c = cur_color
        html_sections.append(
            '<div style="margin-bottom:20px;border-radius:8px;overflow:hidden;border:1.5px solid ' + c["border"] + ';"><div style="background:' + c["border"] + ';padding:9px 18px;"><span style="color:#fff;font-size:12px;font-weight:700;letter-spacing:0.09em;text-transform:uppercase;">' + cur_title + '</span></div><div style="background:' + c["bg"] + ';padding:16px 18px 12px;">' + inner + '</div></div>'
        )

    body = "\n".join(html_sections)
    tags = ["RBA", "ASIC", "AUSTRAC", "APRA", "FATF", "AFCA", "OAIC", "Treasury AU", "ACMA"]
    tag_html = "".join('<span style="display:inline-block;background:rgba(255,255,255,0.1);color:#CBD8E4;font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;margin-right:4px;">' + tag + '</span>' for tag in tags)

    return """<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:-apple-system,Helvetica Neue,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f2f5;padding:32px 0;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0" style="max-width:620px;width:100%;">
  <tr><td>
  <div style="background:#0D1B2A;border-radius:10px 10px 0 0;padding:24px 28px 20px;">
    <div style="font-size:11px;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;color:#5B9BD5;margin-bottom:6px;">Weekly Intelligence Briefing</div>
    <div style="font-size:22px;font-weight:700;color:#ffffff;margin-bottom:4px;">AU Payments &amp; Financial Services Monitor</div>
    <div style="font-size:13px;color:#8BA7C0;">""" + today + """</div>
    <div style="margin-top:12px;">""" + tag_html + """</div>
  </div>
  </td></tr>
  <tr><td style="background:#ffffff;padding:24px 28px;border-radius:0 0 10px 10px;">
    """ + body + """
    <div style="margin-top:28px;padding-top:16px;border-top:1px solid #e8e8e8;text-align:center;">
      <p style="font-size:11px;color:#aaa;margin:0;">Generated automatically · Claude API + web search · Every Monday 7:30 AM AEDT</p>
    </div>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""


# ── Email sender ─────────────────────────────────────────────────
def send_email(report_text):
    sender = os.environ["EMAIL_SENDER"]
    password = os.environ["EMAIL_PASSWORD"]
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    recipients_raw = os.environ["EMAIL_RECIPIENT_PAYMENTS"]
    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
    today = datetime.now().strftime("%d %B %Y")
    subject = "AU Payments & Financial Services Monitor — Weekly Briefing " + today
    html_body = render_html(report_text, today)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(report_text, "plain"))
    msg.attach(MIMEText(html_body, "html"))
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, recipients, msg.as_string())
    print("Email sent to: " + ", ".join(recipients))


if __name__ == "__main__":
    run_monitor()
