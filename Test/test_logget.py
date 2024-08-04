from flask import Flask, request
app = Flask(__name__)

@app.route('/log', methods=['POST'])
def receive_log():
    log_data = request.data.decode('utf-8')
    # 在这里处理接收到的日志数据
    print(log_data)
    return 'Log received successfully', 200


if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True)