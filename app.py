from flask import Flask, request, jsonify
import os
import json
import asyncio
from playwright.async_api import async_playwright

app = Flask(__name__)

# Define the fields that should be extracted
FIELDS_TO_EXTRACT = [
    "Country Name", "Country Code", "State", 
    "District", "City", "Postal Code", 
    "Latitude", "Longitude"
]

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    else:
        return request.remote_addr

async def fetch_ip_info(ip_address):
    url = f"https://scamalytics.com/ip/{ip_address}"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)

        # Extract the IP address
        ip_info = await page.text_content('h1')
        if ip_info and 'Fraud Risk' in ip_info:
            ip_info = ip_info.split()[0]
        else:
            ip_info = "Unknown IP"

        # Extract the Fraud Score
        fraud_score = await page.text_content('.score')
        if fraud_score:
            fraud_score = fraud_score.replace('Fraud Score: ', '').strip()
        else:
            fraud_score = "No score available"

        # Extract additional data
        data_text = await page.text_content('.panel_body')
        if not data_text:
            data_text = "No additional data available"

        # Extract the geographical and other details (filtered by FIELDS_TO_EXTRACT)
        details = {}
        table_rows = await page.query_selector_all('tr')
        for row in table_rows:
            th = await row.query_selector('th')
            td = await row.query_selector('td')
            if th and td:
                field_name = (await th.text_content()).strip()
                if field_name in FIELDS_TO_EXTRACT:
                    details[field_name] = (await td.text_content()).strip()

        await browser.close()

        # Create the response data
        return {
            "ip address": ip_info,
            "Fraud Score": fraud_score,
            "Geographical Details": details,
            "data": data_text
        }

@app.route('/myip', methods=['GET'])
async def get_ip_info():
    ip_address = request.args.get('address') or get_client_ip()

    try:
        # Fetch IP information using Playwright
        response_data = await fetch_ip_info(ip_address)

        # Use json.dumps to pretty-print the response
        return app.response_class(
            response=json.dumps(response_data, indent=4),  # Pretty-print with indent
            mimetype='application/json'
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
