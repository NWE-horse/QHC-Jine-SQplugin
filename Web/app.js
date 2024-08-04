const express = require('express');
const fs = require('fs').promises;
const yaml = require('js-yaml');
const ini = require('ini');

const app = express();
const PORT = process.env.PORT || 43333;

app.use(express.static('html'));
// 中间件：用于解析 JSON 请求体
app.use(express.json());

async function Get_config() {
    try {

    // 读取YAML文件
    const yamlData = await fs.readFile('../Data/server-rule.yaml', 'utf8');

    // 将YAML转换为JSON
    const jsonData = yaml.load(yamlData);

    // 输出JSON
    return  jsonData;
    } catch (error) {
        console.error('读取配置文件错误:', error);
        throw error; // 抛出错误以便调用方处理
    }
}
async function Get_Sign_User(){
    try {
    // 读取 INI 文件
    const iniData = await fs.readFile('../Data/sign.ini', 'utf8');

    // 解析 INI 数据
    const signData = ini.parse(iniData);

    // 输出INI 数据
    return signData
    } catch (error) {
        console.error('读取配置文件错误:', error);
        throw error; // 抛出错误以便调用方处理
    }
}

app.get('/',async (req,res) =>{
    const clientIP = req.headers['x-forwarded-for'] || req.connection.remoteAddress;
    try {
        console.info(`[HTTP] ${clientIP} Success request website`)
        res.sendFile(__dirname + '/html/index.html');
    }catch (error){
        console.error(`[HTTP] ${req.ip} Error request website`,error)
        res.status(404).json({ error: 'Unable to request website.' });
    }
});

app.get('/configData',async (req, res)=>{
    const clientIP = req.headers['x-forwarded-for'] || req.connection.remoteAddress;
    try {
        const configData = await Get_config();
        console.info(`[HTTP] ${clientIP} Success retrieving server data`);
        res.json(configData);
    } catch (error) {
        console.error(`[HTTP] ${clientIP} Error retrieving server data:`, error);
        res.status(404).json({ error: 'Unable to retrieve server data.' });
    }
});

app.get('/signData',async (req, res)=>{
    const clientIP = req.headers['x-forwarded-for'] || req.connection.remoteAddress;
    try {
        const signData = await Get_Sign_User();
        console.info(`[HTTP] ${clientIP} Success retrieving server data`);
        res.json(signData);
    } catch (error) {
        console.error(`[HTTP] ${clientIP} Error retrieving server data:`, error);
        res.status(404).json({ error: 'Unable to retrieve server data.' });
    }
});

app.listen(PORT, () => {
    console.info(`Run success http://localhost:${PORT}`);
});