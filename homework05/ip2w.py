import requests
from requests import exceptions
import json
import socket
import time
import os


def get(url, params={}, timeout=5, max_retries=5, backoff_factor=0.3):
    for n in xrange(max_retries):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            return r
        except requests.exceptions.RequestException:
            if n == max_retries - 1:
                raise
            backoff_value = backoff_factor * (2 ** n)
            time.sleep(backoff_value)


def get_ipinfo(ip):
    url = "https://ipinfo.io/{ip}".format(ip=ip)
    try:
        response = get(url)
    except requests.exceptions.RequestException as err:
        return {"status": err.response.status_code, "message": err.message}
    try:
        return response.json()
    except ValueError as err:
        return {"status": response.status_code, "message": err.message}


def get_weather(lat, lon, appid):
    url = "http://api.openweathermap.org/data/2.5/weather"
    try:
        response = get(url, params={
            "lat": lat,
            "lon": lon,
            "units": "metric",
            "APPID": appid
        })
    except requests.exceptions.RequestException as err:
        return {"status": err.response.status_code, "message": err.message}
    try:
        return response.json()
    except ValueError as err:
        return {"status": response.status_code, "message": err.message}


def is_valid(ip):
    try:
        socket.inet_aton(ip)
        return True
    except socket.error:
        return False


def application(env, start_response):

    def response_with_error(status='400', message=''):
        response_body = json.dumps({"error": message})
        response_headers = [
            ('Content-Type', 'application/json'),
            ('Content-Length', str(len(response_body)))
        ]
        start_response(status, response_headers)
        return [response_body]

    uri = env.get("REQUEST_URI", "")
    ip = uri.split('/')[-1]
    if not is_valid(ip):
        return response_with_error(message="Invalid IP address")

    appId = os.environ.get("WEATHER_APPID")
    if not appId:
        return response_with_error(message="Set the environment variable WEATHER_APPID")

    ipinfo = get_ipinfo(ip)
    if "bogon" in ipinfo:
        # 127.0.0.1, 0.0.0.0 and so on
        return response_with_error(message="IP address is a bogon")
    elif "status" in ipinfo:
        return response_with_error(
            status=ipinfo["status"],
            message=ipinfo["message"]
        )

    try:
        lat, lon = ipinfo["loc"].split(",")
    except KeyError:
        return response_with_error(message="Invalid JSON-scheme (ipinfo)")

    weather_data = get_weather(lat, lon, appId)
    if "status" in weather_data:
        return response_with_error(
            status=weather_data["status"],
            message=weather_data["message"]
        )

    try:
        city = weather_data["name"]
        temp = weather_data["main"]["temp"]
        description = weather_data["weather"][0]["description"]
    except (KeyError, IndexError):
        return response_with_error(message="Invalid JSON-scheme (openweathermap)")

    response_body = json.dumps({
        "city": city,
        "temp": temp,
        "conditions": description
    })

    status = '200 OK'
    response_headers = [
        ('Content-Type', 'application/json'),
        ('Content-Length', str(len(response_body)))
    ]

    start_response(status, response_headers)
    return [response_body]

