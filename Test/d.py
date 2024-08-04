import requests

end_json = {
    'steamid': '8666',
    'timeStats': 8888888
}

url = 'http://150.138.84.157:3000/sqlite/gameTime'
requests.post(url=url, json=end_json)
