from datetime import datetime
import time
from flask import Flask, jsonify, render_template, make_response, request
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import requests

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'


BASE_URL = "http://114.134.71.136:8080/api"
HEADERS = None
DEVICE_ID = "3af6c030-0138-11ee-8c68-d371b81349fd"


def get_token():
    token = request.headers.get('X-Authorization')
    return token

@app.before_request
def initialize():
    global HEADERS
    token = get_token()
    HEADERS = {"X-Authorization": f"{token}"}

# Define reusable functions
def get_device_info(device_id):
    endpoint = f"{BASE_URL}/device/{device_id}"
    response = requests.get(endpoint, headers=HEADERS)
    return response.json()

def get_customer_name(customer_id):
    endpoint = f"{BASE_URL}/customer/{customer_id}/title" 
    response = requests.get(endpoint, headers=HEADERS)
    return response.text.strip()

def get_telemetry_info(key):
    endpoint = f"http://114.134.71.136:8000/api/telemetry/{key}"
    response = requests.get(endpoint, headers=HEADERS)
    return response.json()

def get_timeseries_data(device_id, key, start, end):
    endpoint = f"{BASE_URL}/plugins/telemetry/DEVICE/{device_id}/values/timeseries?agg=NONE&keys={key}&startTs={start}&endTs={end}"
    response = requests.get(endpoint, headers=HEADERS)
    return response.json()

def format_datetime(timestamp):
    dt = datetime.fromtimestamp(int(timestamp) / 1000)  
    return dt.strftime("%d %b %Y %H:%M")

def extract_timeseries(data):
    ts_values = []
    value_values = []
    
    for item in sorted(data, key=lambda x: x['ts']):
        ts_formatted = format_datetime(item['ts'])
        value = item['value']
        
        ts_values.append(ts_formatted) 
        value_values.append(value)

    return ts_values, value_values


def calculate_stats(values):
    values_num = [float(x) for x in values]   
    return {
        "max": max(values_num),
        "min": min(values_num),
        "avg": round(sum(values_num) / len(values_num),2)
    }

# ini perhitungan volume usage
def calculate_usage_values(formatted_values):
    calculated_values = []
    for i in range(len(formatted_values)):
        if i == 0:
            D = 0
        else:
            A = formatted_values[i - 1]
            B = formatted_values[i]
            C = formatted_values[i - 1]
            if C <= A and B > A:
                D = B - A + C
            elif C > A and B > A:
                D = C + B
            else:
                D = 0  

        calculated_values.append(round(D, 2))
    return calculated_values
@app.route('/<startTs>/<endTs>')
def index(startTs,endTs):
    
    # Fetch data
    device_data = get_device_info(DEVICE_ID)
    device_name = device_data["name"]
    
    customer_name = get_customer_name("1261be20-40c3-11ee-8c68-d371b81349fd")
    
    cpu_info = get_telemetry_info("cpu")
    cpu_unit = cpu_info["telemetry_value"][0]["unit"]
    cpu_name = cpu_info["name_telemetry"]
    usage_info = get_telemetry_info("usage")
    usage_unit = usage_info["telemetry_value"][0]["unit"]
    usage_name = usage_info["name_telemetry"]
    t_info = get_telemetry_info("t")
    t_unit = t_info["telemetry_value"][0]["unit"]
    t_name = t_info["name_telemetry"]
    
    start, end = startTs, endTs
    cpu_data = get_timeseries_data(DEVICE_ID, "cpu", start, end)
    usage1_data = get_timeseries_data(DEVICE_ID, "usage1", start, end)
    usage2_data = get_timeseries_data(DEVICE_ID, "usage2", start, end)
    t_data = get_timeseries_data(DEVICE_ID, "t", start, end)
    
    # Process data
    start_dt = format_datetime(start) 
    end_dt = format_datetime(end)
    
    cpu_ts_values, cpu_value_values = extract_timeseries(cpu_data["cpu"]) 
    cpu_stats = calculate_stats(cpu_value_values)
    
    usage1_ts_values, usage1_value_values = extract_timeseries(usage1_data["usage1"])
    formatted_usage1_values = [round(float(x)/1000000, 2) for x in usage1_value_values]
    usage1_stats = calculate_stats(formatted_usage1_values)
    calculated_usage1_values = calculate_usage_values(formatted_usage1_values)

    usage2_ts_values, usage2_value_values = extract_timeseries(usage2_data["usage2"])
    formatted_usage2_values = [round(float(x)/1000000, 2) for x in usage2_value_values]
    usage2_stats = calculate_stats(formatted_usage2_values)
    calculated_usage2_values = calculate_usage_values(formatted_usage2_values)




    t_ts_values, t_value_values = extract_timeseries(t_data["t"]) 
    t_stats = calculate_stats(t_value_values)


    # HTML
    html = render_template(
        "template.jinja",
        device_name=device_name,
        customer_name=customer_name,
        start_date=start_dt,
        end_date=end_dt, 
        cpu_unit=cpu_unit,
        cpu_stats=cpu_stats,
        cpu_name=cpu_name,
        cpu_ts_values=cpu_ts_values,
        cpu_value_values=cpu_value_values,
        usage_unit=usage_unit,
        usage_name=usage_name,
        usage1_stats=usage1_stats,
        usage1_ts_values=usage1_ts_values,
        usage1_value_values=calculated_usage1_values,
        usage2_stats=usage2_stats,
        usage2_ts_values=usage2_ts_values,
        usage2_value_values=calculated_usage2_values,
        t_unit=t_unit,
        t_name=t_name,
        t_stats=t_stats,
        t_ts_values=t_ts_values,
        t_value_values=t_value_values

    )


    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    # Inisialisasi driver
    driver = webdriver.Chrome(options=chrome_options)

    # Mendapatkan token dari header
    token = get_token()

    # Membuat header dengan token
    headers = {
        'X-Authorization': f'{token}',
    }
    
    print(headers)
    for key, value in headers.items():
        chrome_options.add_argument(f'--header={key}: {value}')


    # Permasalahannya disini sudah di set token masih belum bisa
    driver.get(f'http://localhost:5000/{start}/{end}')

    time.sleep(5)

    driver.save_screenshot('screenshot.png')


    import img2pdf
    with open("screenshot.pdf", "wb") as f:
        f.write(img2pdf.convert("screenshot.png"))

    

    return make_response(html, 200)
if __name__ == '__main__':
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000
    )