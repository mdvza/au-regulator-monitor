"""
AU Regulator Monitor — e-commerce
Monitors ACCC and other Australian regulators via Claude API with web search.
Also scrapes top-tier Australian law firms for relevant insights.
Sends a weekly briefing email.
"""

import anthropic
import smtplib
import os
import time
import requests
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ── Model configuration ──────────────────────────────────────────
# Change the model in ONE place. Override via the CLAUDE_MODEL env
# variable / GitHub Actions secret without editing the code.
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")

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
- Do not include ANY preamble, meta-commentary, or explanation of what you are doing.
- Your response MUST start with the exact text: EXECUTIVE SUMMARY (on its own line).
- Never write introductory sentences before EXECUTIVE SUMMARY.
- Never combine section headers with other text on the same line.
- For each update, you MUST include the exact URL of the specific page, press release, or document you found during web search. Format: [Read more](https://exact-url.com)
- The URL must point to the specific article, press release, media release, consultation paper, or enforcement notice — NOT to a homepage or section index.
- Good example: https://www.accc.gov.au/media-release/accc-takes-action-against-xyz (specific press release)
- Bad example: https://www.accc.gov.au (homepage) or https://www.accc.gov.au/media-release (index page)
- If you found the information via web search, use the exact URL from the search result.
- Prefer official sources in this order: (1) regulator's own website, (2) government legislation or consultation page, (3) law firm insight page. Never link to paywalled content or news aggregators.

---

STRUCTURE TO FOLLOW:

EXECUTIVE SUMMARY
[2-3 sentences summarising the most important developments this week and their significance for e-commerce platforms.]

---

1. ACCC (Australian Competition and Consumer Commission)

For each update, use this format:
• **[Title]** — [Date if known]
[2-3 sentence summary of what happened and why it matters for e-commerce platforms.] [Read more](https://exact-url-to-specific-page.com)

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

    # Step 2: Call Claude with web search (with retry logic)
    print(f"Calling Claude API with web search (model: {MODEL})...")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    max_attempts = 3
    response = None
    for attempt in range(max_attempts):
        try:
            response = client.messages.create(
                model=MODEL,
                max_tokens=4000,
                tools=[{"type": "web_search_20250305", "name": "web_search"}],
                messages=[{"role": "user", "content": build_query(law_firm_content)}]
            )
            break  # success — exit retry loop
        except anthropic.InternalServerError as e:
            if attempt < max_attempts - 1:
                wait = 60 * (attempt + 1)  # 60s first retry, 120s second
                print(f"API InternalServerError (attempt {attempt+1}/{max_attempts}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"API InternalServerError after {max_attempts} attempts. Giving up.")
                raise
        except anthropic.RateLimitError as e:
            if attempt < max_attempts - 1:
                print(f"Rate limit hit (attempt {attempt+1}/{max_attempts}), retrying in 60s...")
                time.sleep(60)
            else:
                print(f"Rate limit error after {max_attempts} attempts. Giving up.")
                raise

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


# ── Section colour map ───────────────────────────────────────────
SECTION_COLORS = {
    "accc":            {"bg": "#EBF4FF", "border": "#2B7FD4", "label": "#1A5FA8"},
    "oaic":            {"bg": "#EDF7F2", "border": "#2BA876", "label": "#1A7A52"},
    "treasury":        {"bg": "#FFF8EB", "border": "#D4902B", "label": "#A86A1A"},
    "acma":            {"bg": "#F3EEFF", "border": "#7B5EA7", "label": "#5A3D8A"},
    "law firm":        {"bg": "#FFF0F0", "border": "#D45A5A", "label": "#A83030"},
    "action items":    {"bg": "#F0F9FF", "border": "#2BB5D4", "label": "#1A8AA8"},
    "executive":       {"bg": "#F8F8F8", "border": "#AAAAAA", "label": "#444444"},
}

def get_section_color(title):
    t = title.lower()
    for key, val in SECTION_COLORS.items():
        if key in t:
            return val
    return {"bg": "#F4F6F8", "border": "#AAAAAA", "label": "#333333"}

def render_html(report_text, today):
    lines = report_text.split("\n")
    blocks = []
    current_section_color = None
    current_section_lines = []
    current_section_title = None

    def flush_section():
        if current_section_title is None:
            return ""
        c = current_section_color
        inner = "".join(current_section_lines)
        return f"""
        <div style="margin-bottom:24px; border-radius:8px; overflow:hidden; border:1px solid {c['border']};">
          <div style="background:{c['border']}; padding:10px 18px;">
            <span style="color:#ffffff; font-size:13px; font-weight:700; letter-spacing:0.08em; text-transform:uppercase;">{current_section_title}</span>
          </div>
          <div style="background:{c['bg']}; padding:16px 18px;">
            {inner}
          </div>
        </div>"""

    def render_line(stripped):
        if not stripped or stripped == "---":
            return ""
        # Bullet points
        if stripped.startswith("• ") or stripped.startswith("- "):
            content = stripped[2:]
            content = apply_bold(content)
            return f'<p style="margin:5px 0 5px 12px; color:#333; font-size:14px; line-height:1.65;">&#8226;&nbsp;{content}</p>'
        # Update titles (bold standalone lines like **Title** — date)
        if stripped.startswith("**") and "**" in stripped[2:]:
            end = stripped.index("**", 2)
            title_text = stripped[2:end]
            rest = stripped[end+2:].strip(" —-")
            date_html = f'<span style="color:#888; font-size:12px; margin-left:8px;">{rest}</span>' if rest else ""
            return f'<p style="margin:14px 0 4px; font-size:14px; font-weight:700; color:#1a1a2e;">{title_text}{date_html}</p>'
        # Regular paragraph
        return f'<p style="margin:5px 0; color:#444; font-size:14px; line-height:1.7;">{apply_bold(stripped)}</p>'

    def apply_bold(text):
        import re
        # Convert markdown links [text](url) to HTML anchors
        text = re.sub(
            r'\[([^\]]+)\]\((https?://[^\)]+)\)',
            r'<a href="\2" style="color:#2B7FD4;text-decoration:none;font-weight:600;">\1 ↗</a>',
            text
        )
        # Convert **bold**
        parts = text.split("**")
        result = ""
        for i, part in enumerate(parts):
            if i % 2 == 1:
                result += f"<strong>{part}</strong>"
            else:
                result += part
        return result

    # Identify section headers - also handle cases where header appears mid-line
    import re
    # Pre-process: split lines on known section headers that appear mid-line
    processed_lines = []
    header_split = re.compile(
        r'(EXECUTIVE SUMMARY|ACTION ITEMS|\d+\.\s+(?:ACCC|OAIC|TREASURY|ACMA|LAW FIRM)[^\n]*)',
        re.IGNORECASE
    )
    for line in lines:
        parts = header_split.split(line)
        if len(parts) > 1:
            for part in parts:
                if part.strip():
                    processed_lines.append(part.strip())
        else:
            processed_lines.append(line)
    lines = processed_lines

    section_pattern = re.compile(
        r'^(EXECUTIVE SUMMARY|ACTION ITEMS|\d+\.\s+(ACCC|OAIC|TREASURY|ACMA|LAW FIRM))',
        re.IGNORECASE
    )

    html_sections = []
    cur_title = None
    cur_color = None
    cur_lines_html = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped == "---":
            continue
        m = section_pattern.match(stripped)
        if m:
            # Flush previous section
            if cur_title:
                inner = "".join(cur_lines_html)
                c = cur_color
                html_sections.append(f"""
                <div style="margin-bottom:20px;border-radius:8px;overflow:hidden;border:1.5px solid {c['border']};">
                  <div style="background:{c['border']};padding:9px 18px;">
                    <span style="color:#fff;font-size:12px;font-weight:700;letter-spacing:0.09em;text-transform:uppercase;">{cur_title}</span>
                  </div>
                  <div style="background:{c['bg']};padding:16px 18px 12px;">{inner}</div>
                </div>""")
            cur_title = stripped
            cur_color = get_section_color(stripped)
            cur_lines_html = []
        else:
            cur_lines_html.append(render_line(stripped))

    # Flush last section
    if cur_title:
        inner = "".join(cur_lines_html)
        c = cur_color
        html_sections.append(f"""
        <div style="margin-bottom:20px;border-radius:8px;overflow:hidden;border:1.5px solid {c['border']};">
          <div style="background:{c['border']};padding:9px 18px;">
            <span style="color:#fff;font-size:12px;font-weight:700;letter-spacing:0.09em;text-transform:uppercase;">{cur_title}</span>
          </div>
          <div style="background:{c['bg']};padding:16px 18px 12px;">{inner}</div>
        </div>""")

    body = "\n".join(html_sections)

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:-apple-system,Helvetica Neue,Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f2f5;padding:32px 0;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0" style="max-width:620px;width:100%;">

  <!-- Header -->
  <tr><td>
  <div style="background:#0D1B2A;border-radius:10px 10px 0 0;padding:24px 28px 20px;">
    <div style="font-size:11px;font-weight:700;letter-spacing:0.15em;text-transform:uppercase;color:#5B9BD5;margin-bottom:6px;">Weekly Intelligence Briefing</div>
    <div style="font-size:22px;font-weight:700;color:#ffffff;margin-bottom:4px;">AU Regulator Monitor</div>
    <div style="font-size:13px;color:#8BA7C0;">{today}</div>
    <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;">
      {"".join([f'<span style="display:inline-block;background:rgba(255,255,255,0.1);color:#CBD8E4;font-size:11px;font-weight:600;padding:3px 10px;border-radius:20px;margin-right:4px;">{tag}</span>' for tag in ["ACCC","OAIC","Treasury AU","ACMA","Law Firms"]])}
    </div>
  </div>
  </td></tr>

  <!-- Content -->
  <tr><td style="background:#ffffff;padding:24px 28px;border-radius:0 0 10px 10px;">
    {body}
    <div style="margin-top:28px;padding-top:16px;border-top:1px solid #e8e8e8;text-align:center;">
      <p style="font-size:11px;color:#aaa;margin:0;">Generated automatically · Claude API + web search + law firm scraping · Every Monday 7:00 AM AEDT</p>
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

    # Support multiple recipients separated by commas
    # e.g. EMAIL_RECIPIENT = "matteo@ebay.com, colleague1@ebay.com, colleague2@ebay.com"
    recipients_raw = os.environ["EMAIL_RECIPIENT"]
    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]

    today = datetime.now().strftime("%d %B %Y")
    subject = f"AU Regulator Monitor — Weekly Briefing {today}"
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

    print(f"Email sent to: {', '.join(recipients)}")


if __name__ == "__main__":
    run_monitor()
