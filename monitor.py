name: AU Regulator Monitor

on:
  schedule:
    - cron: "0 20 * * 0"
  workflow_dispatch:

jobs:
  monitor:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run regulator monitor
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          EMAIL_SENDER: ${{ secrets.EMAIL_SENDER }}
          EMAIL_RECIPIENT: ${{ secrets.EMAIL_RECIPIENT }}
          EMAIL_PASSWORD: ${{ secrets.EMAIL_PASSWORD }}
          SMTP_HOST: smtp.gmail.com
          SMTP_PORT: "587"
        run: python monitor.py
