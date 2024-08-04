/* Simple Rcon Client by Mattt */
const net = require('net');
const { Buffer } = require('buffer');
const { EventEmitter } = require('events');
const http = require('http');
class RconConnection {
  constructor() {
    this.events = new EventEmitter();
    this.netConnection;
    this.stream = new Buffer.alloc(0);
    this.responseString = "";
    this.type = { auth: 0x03, command: 0x02, response: 0x00, server: 0x01 };
    this.soh = { size: 7, id: 0, type: this.type.response, body: "" };
  }
  connect({ port, host, token }) {
    this.netConnection = net.createConnection({ port: port, host: host }, () => this.#write(this.type.auth, 2147483647, token));
    this.netConnection.on("data", (data) => this.#onData(data));
    this.netConnection.on("end", () => this.events.emit("end"));
  }
  send(body, id = 99) {
    this.#write(this.type.command, id, body);
    this.#write(this.type.command, id + 2);
  }
  #write(type, id, body) {
    this.netConnection.write(this.#encode(type, id, body).toString("binary"), "binary");
  }
  #encode(type, id, body = "") {
    const size = Buffer.byteLength(body) + 14;
    const buffer = new Buffer.alloc(size);
    buffer.writeInt32LE(size - 4, 0);
    buffer.writeInt32LE(id, 4);
    buffer.writeInt32LE(type, 8);
    buffer.write(body, 12, size - 2, "utf8");
    buffer.writeInt16LE(0, size - 2);
    return buffer;
  }
  #onData(data) {
    this.stream = Buffer.concat([this.stream, data], this.stream.byteLength + data.byteLength);
    while (this.stream.byteLength >= 4) {
      const packet = this.#decode();
      if (!packet) break;
      else if (packet.type === this.type.response) this.#onResponse(packet);
      else if (packet.type === this.type.server) this.events.emit("server", packet.body);
      else if (packet.type === this.type.command) this.events.emit("auth");
    }
  }
  #decode() {
    if (this.stream[0] === 0 && this.stream[1] === 1 && this.stream[2] === 0 && this.stream[3] === 0 && this.stream[4] === 0 && this.stream[5] === 0 && this.stream[6] === 0) {
      this.stream = this.stream.subarray(7);
      return this.soh;
    }
    const bufSize = this.stream.readInt32LE(0);
    if (bufSize <= this.stream.byteLength - 4) {
      const response = { size: bufSize, id: this.stream.readInt32LE(4), type: this.stream.readInt32LE(8), body: this.stream.toString("utf8", 12, bufSize + 2) };
      this.stream = this.stream.subarray(bufSize + 4);
      return response;
    } else return null;
  }
  #onResponse(packet) {
    if (packet.body === "") console.log(packet);
    else {
      // this.events.emit("response", this.responseString);
      this.responseString = "";
    }
  }
}

// 发送数据到 Express 服务器的函数
function sendDataToServer(data) {
    const postData = JSON.stringify(data);
    const options = {
        hostname: 'localhost',
        port: 5004,
        path: '/server-data',
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(postData)
        }
    };

    const req = http.request(options, (res) => {
        res.on('data', (chunk) => {
        });
    });

    req.on('error', (e) => {
        console.error(`请求遇到问题：${e.message}`);
    });

    req.write(postData);
    req.end();
}

const servers = [
    { serverId: 'mxxy', port: "25001", host: "180.188.21.82", token: "9UneFErmhxU6Knmreo9QSbgVQiRXyLrt" },
    { serverId: 'mxth', port: "25009", host: "180.188.21.82", token: "GJUs0fx6G8jtrRtY" },
     { serverId: 'qgxy', port: "25003", host: "180.188.21.82", token: "3$wnSazw%qZ3bVAsmN" },
     { serverId: 'qgth', port: "25004", host: "180.188.21.82", token: "4#6ecS2p%Gp9Gms2B2" },
     {serverId: 'wzll',port: "25007", host: "180.188.21.82", token: "886adf" }
    // Add more server configurations as needed
];
// 修改原有代码，将数据发送到 Express 服务器
const squadRcon = (servers) => {
  servers.forEach(server => {
    const rcon = new RconConnection();

    const connectAndSetup = () => {
      rcon.connect(server);

      rcon.interval = setInterval(() => {
        rcon.send("ListPlayers");
      }, 10000); // 10000 milliseconds = 10 seconds

      rcon.events.on("response", (str) => {
          console.log(str)
        // sendDataToServer({ serverId: server.serverId, serverData: str });
      });

      rcon.events.on("auth", () => {
        rcon.send("ListPlayers");
      });

      rcon.events.on("end", () => {
        clearInterval(rcon.interval);
      });

      rcon.events.on("error", (err) => {
        if (err === 'read ECONNRESET') {
          console.error(`连接被重置或拒绝: ${server.serverId}`, err);
          clearInterval(rcon.interval);
          setTimeout(() => connectAndSetup(), 60000); // Reconnect after 1 minute
        } else {
          console.error(`服务器 ${server.serverId} 出现错误:`, err);
        }
      });
    };

    // 使用 try-catch 包装 connectAndSetup 调用，防止初始化错误
    try {
      connectAndSetup();
    } catch (err) {
      console.error(`服务器 ${server.serverId} 初始化连接失败:`, err);
    }

    // 在 RconConnection 实例上处理未捕获的错误事件
    rcon.events.on('error', (err) => {
      console.error(`未处理的错误: ${server.serverId}`, err);
    });
  });
};

// 全局捕获未处理的异常
process.on('uncaughtException', (err) => {
  console.error('未捕获的异常:', err);
});
squadRcon(servers);