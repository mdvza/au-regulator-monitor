"""
AU Regulator Monitor — e-commerce
Monitors ACCC and other Australian regulators via Claude API with web search.
Also scrapes top-tier Australian law firms for relevant insights.
Sends a weekly briefing email.
"""

import anthropic
import smtplib
import os
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ── Law firm sources ─────────────────────────────────────────────
LAW_FIRM_SOURCES = [
    {
        "name": "Gilbert + Tobin",
        "url": "https://www.gtlaw.com.au/knowledge",
        "selector": "h3, h2, .article-title, .insight-title"
    },
    {
        "name": "Clayton Utz",
        "url": "https://www.claytonutz.com/knowledge",
        "selector": "h3, h2, .article-title, .insight-title"
    },
    {
        "name": "Allens",
        "url": "https://www.allens.com.au/insights/",
        "selector": "h3, h2, .article-title, .insight-title"
    },
    {
        "name": "King & Wood Mallesons",
        "url": "https://www.kwm.com/en/au/knowledge/insights.html",
        "selector": "h3, h2, .article-title, .insight-title"
    },
    {
        "name": "Herbert Smith Freehills",
        "url": "https://www.herbertsmithfreehills.com/insights",
        "selector": "h3, h2, .article-title, .insight-title"
    },
]

# ── Scrape law firm insights ─────────────────────────────────────
def scrape_law_firms():
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    results = []
    for firm in LAW_FIRM_SOURCES:
        try:
            resp = requests.get(firm["url"], headers=headers, timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                items = soup.select(firm["selector"])
                titles = []
                for item in items[:10]:
                    text = item.get_text(strip=True)
                    if len(text) > 20:
                        titles.append(text)
                if titles:
                    results.append(f"**{firm['name']}** ({firm['url']}):\n" + "\n".join(f"- {t}" for t in titles[:8]))
                else:
                    results.append(f"**{firm['name']}**: No recent articles found (site may block scraping).")
            else:
                results.append(f"**{firm['name']}**: Could not access site (status {resp.status_code}).")
        except Exception as e:
            results.append(f"**{firm['name']}**: Error accessing site ({str(e)[:60]}).")
    return "\n\n".join(results)


# ── Main query ───────────────────────────────────────────────────
def build_query(law_firm_content):
    today = datetime.now().strftime("%d %B %Y")
    return f"""You are a senior legal counsel specialising in Australian competition law, consumer protection, and digital regulation.

Today is {today}. Prepare a professional weekly briefing on regulatory developments in Australia relevant to e-commerce platforms and online marketplaces (such as eBay, Amazon, Catch).

IMPORTANT INSTRUCTIONS:
- Write entirely in clear, plain English. No Italian. No other languages.
- Be concise and professional. Each update should be 2-4 sentences maximum.
- Use the exact structure below. Do not deviate from it.
- Do not include any preamble, meta-commentary, or explanation of what you are doing.
- Start directly with the Executive Summary.

---

STRUCTURE TO FOLLOW:

EXECUTIVE SUMMARY
[2-3 sentences summarising the most important developments this week and their significance for e-commerce platforms.]

---

1. ACCC (Australian Competition and Consumer Commission)

For each update, use this format:
• [Title] — [Date if known]
[2-3 sentence summary of what happened and why it matters for e-commerce platforms.]

Search for and include:
- Enforcement actions and investigations
- Statements on digital platforms and marketplaces
- Updates to the Digital Platform Services Inquiry
- Merger decisions relevant to digital markets
- Consumer protection actions (dark patterns, subscription traps, pricing)
- Misuse of market power (s 46 CCA)

---

2. OAIC (Office of the Australian Information Commissioner)

Same format as above. Search for:
- Privacy Act reform updates
- Enforcement actions against digital companies
- New guidance on data handling and AI
- Automated decision-making (ADM) obligations

---

3. TREASURY AUSTRALIA

Same format. Search for:
- Digital competition regime developments
- Unfair Trading Practices Bill 2026 updates
- Consumer Data Right (CDR) updates
- Reform proposals affecting online platforms

---

4. ACMA (Australian Communications and Media Authority)

Same format. Search for:
- Scam and spam enforcement relevant to e-commerce
- Digital communications regulation updates

---

5. LAW FIRM INSIGHTS
[Summarise any articles from the law firm content below that are relevant to e-commerce, digital platforms, competition law, or privacy. For each, state the firm name, article title, and a 1-2 sentence summary of why it matters.]

Law firm content scraped today:
{law_firm_content if law_firm_content else "No law firm content available this week."}

---

ACTION ITEMS
[Bullet list of concrete actions or deadlines that an e-commerce legal team should be aware of in the next 30-60 days. Be specific.]

---

If there are no updates for a section this week, write: "No significant updates this week."
Do not fabricate or speculate. Only report what you find through web search.
"""


# ── Main function ────────────────────────────────────────────────
def run_monitor():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] Starting AU Regulator Monitor...")

    # Step 1: Scrape law firms
    print("Scraping law firm websites...")
    law_firm_content = scrape_law_firms()
    print("Law firm scraping complete.")

    # Step 2: Call Claude with web search
    print("Calling Claude API with web search...")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": build_query(law_firm_content)}]
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

    # Step 3: Send email
    send_email(report_text)
    return report_text


# ── Email sender ─────────────────────────────────────────────────
def send_email(report_text):
    sender = os.environ["EMAIL_SENDER"]
    recipient = os.environ["EMAIL_RECIPIENT"]
    password = os.environ["EMAIL_PASSWORD"]
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))

    today = datetime.now().strftime("%d %B %Y")
    subject = f"AU Regulator Monitor — Weekly Briefing {today}"

    # Convert plain text to clean HTML
    html_lines = []
    for line in report_text.split("\n"):
        stripped = line.strip()
        if not stripped:
            html_lines.append("<br>")
        elif stripped.startswith("# "):
            html_lines.append(f'<h1 style="font-size:20px;color:#1a1a2e;margin:24px 0 8px;">{stripped[2:]}</h1>')
        elif stripped.startswith("## "):
            html_lines.append(f'<h2 style="font-size:17px;color:#1a1a2e;margin:20px 0 6px;border-bottom:1px solid #e0e0e0;padding-bottom:4px;">{stripped[3:]}</h2>')
        elif stripped.startswith("### "):
            html_lines.append(f'<h3 style="font-size:15px;color:#333;margin:16px 0 4px;">{stripped[4:]}</h3>')
        elif stripped.startswith("---"):
            html_lines.append('<hr style="border:none;border-top:1px solid #e0e0e0;margin:16px 0;">')
        elif stripped.startswith("• ") or stripped.startswith("- "):
            html_lines.append(f'<p style="margin:6px 0 6px 16px;color:#333;">&#8226; {stripped[2:]}</p>')
        elif stripped.startswith("**") and stripped.endswith("**"):
            html_lines.append(f'<p style="font-weight:600;color:#1a1a2e;margin:12px 0 4px;">{stripped[2:-2]}</p>')
        else:
            # Handle inline bold (**text**)
            formatted = stripped
            while "**" in formatted:
                formatted = formatted.replace("**", "<strong>", 1).replace("**", "</strong>", 1)
            html_lines.append(f'<p style="margin:4px 0;color:#333;line-height:1.6;">{formatted}</p>')

    html_body = f"""
    <html><body style="font-family: -apple-system, Arial, sans-serif; max-width: 680px; margin: auto; padding: 24px; color: #222;">

    <div style="background: #1a1a2e; padding: 20px 24px; border-radius: 8px; margin-bottom: 28px;">
        <h1 style="margin:0; color: #ffffff; font-size: 20px; font-weight: 600;">AU Regulator Monitor</h1>
        <p style="margin: 6px 0 0; color: #aab; font-size: 13px;">Weekly Briefing — {today}</p>
        <p style="margin: 4px 0 0; color: #aab; font-size: 12px;">
            ACCC &nbsp;·&nbsp; OAIC &nbsp;·&nbsp; Treasury AU &nbsp;·&nbsp; ACMA &nbsp;·&nbsp; Law Firm Insights
        </p>
    </div>

    {"".join(html_lines)}

    <hr style="margin-top: 36px; border: none; border-top: 1px solid #e0e0e0;">
    <p style="font-size: 11px; color: #999; margin-top: 12px;">
        Generated automatically by AU Regulator Monitor · Claude API + web search + law firm scraping<br>
        Runs every Monday at 7:00 AM AEDT
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

    print(f"Email sent to {recipient}")


if __name__ == "__main__":
    run_monitor()
