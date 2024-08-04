from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/logs', methods=['POST'])
def receive_logs():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data received'}), 400
    # 处理接收到的日志
    process_logs(data)
    return jsonify({'message': 'Logs received successfully'}), 200

def process_logs(log_data):
    for entry in log_data.get('entries', []):
        timestamp = entry.get('ts')
        line = entry.get('line')
        print(f'Timestamp: {timestamp}, Log Line: {line}')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)