const express = require('express');
const bodyParser = require('body-parser');
const app = express();
const port = 5004;

// 解析 application/json
app.use(bodyParser.json());

// 存储从服务器接收到的数据
let serverData = {};


// 路由处理器：接收从服务器推送的数据
app.post('/server-data', (req, res) => {
    const { serverId, serverData: newData } = req.body;
    // 更新存储的数据，只替换特定 serverId 的内容
    serverData[serverId] = newData;
    res.send('成功接收服务器数据');
});

// 路由处理器：获取存储的数据
app.get('/get-server-data/:serverId', (req, res) => {
    const { serverId } = req.params;
    const data = serverData[serverId];
    if (data) {
        res.json({ serverData: data });
    } else {
        res.status(404).json({ error: '指定的服务器ID不存在的数据' });
    }
});
// 启动 Express 服务器
app.listen(port, () => {
    console.log(`Express 服务器运行在 http://localhost:${port}`);
});