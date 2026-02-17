from flask import Flask, render_template, request, Response, jsonify
import pandas as pd
import requests
import json
import re
from edgar import Company, set_identity
import google.generativeai as genai

app = Flask(__name__)

# LOAD CONFIG

with open("config.json") as f:
    config = json.load(f)

set_identity(config["EDGAR_IDENTITY"])
genai.configure(api_key=config["GOOGLE_API_KEY"])

model = genai.GenerativeModel("gemini-2.5-flash")

# LOAD S&P500

def load_sp500():
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    tables = pd.read_html(response.text)

    df = tables[0][['Symbol', 'Security']]
    df.columns = ['Ticker', 'Company']
    return df

sp500_df = load_sp500()

# CAM EXTRACTION

def extract_cam(ticker, year):

    c = Company(ticker)
    filings = c.get_filings(form="10-K").latest(10)

    filings_for_year = [
        f for f in filings
        if f.filing_date and f.filing_date.year == year
    ]

    if not filings_for_year:
        return "No 10-K filing found."

    text = filings_for_year[0].text()

    match = re.search(
        r'Critical Audit Matter[s]?(.*?)(?=\n\s*Signature|\Z)',
        text,
        re.IGNORECASE | re.DOTALL
    )

    if match:
        return match.group(0)

    return "CAM section not found."

# ROUTES

@app.route('/')
def dashboard():
    companies = sp500_df.to_dict(orient='records')
    return render_template("dashboard.html", companies=companies)

# Streaming endpoint
@app.route('/stream_cam', methods=['POST'])
def stream_cam():

    company = request.json['company']
    year = int(request.json['year'])

    ticker = sp500_df.loc[
        sp500_df['Company'] == company,
        'Ticker'
    ].values[0]

    cam_text = extract_cam(ticker, year)

    def generate():

        prompt = f"""
        Summarize the following Critical Audit Matter:

        {cam_text}

        Summary:
        """

        response = model.generate_content(
            prompt,
            stream=True
        )

        for chunk in response:
            if hasattr(chunk, "text"):
                yield chunk.text

    return Response(generate(), mimetype='text/plain')

if __name__ == "__main__":
    app.run(debug=True)
