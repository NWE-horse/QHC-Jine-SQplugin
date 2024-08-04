document.addEventListener('DOMContentLoaded', function() {
    // 初始化时从服务器获取配置数据并填充表单
    fetch('/configData')
        .then(response => response.json())
        .then(data => {
            Object.keys(data).forEach(key => {
                const input = document.getElementById(key);
                if (input) {
                    input.value = data[key];
                }
            });
        })
        .catch(error => console.error('Error fetching config:', error));
});

// 获取弹窗
var modal = document.getElementById('popup-window');

// 打开弹窗的按钮对象
var btn = document.getElementById("popup-Btn");

// 获取 <span> 元素，用于关闭弹窗
var span = document.querySelector('.close');

// 点击按钮打开弹窗
btn.onclick = function() {
    modal.style.display = "block";
        // 初始化时从服务器获取配置数据并填充表格
    fetch('/signData')
        .then(response => response.json())
        .then(data => {
            renderData(data)
        })
        .catch(error => console.error('Error fetching config:', error));
}

// 点击 <span> (x), 关闭弹窗
span.onclick = function() {
    modal.style.display = "none";
}

// 在用户点击其他地方时，关闭弹窗
window.onclick = function(event) {
    if (event.target == modal) {
        modal.style.display = "none";
    }
}

function renderData(data){
  const container = document.getElementById('ls');
  container.innerHTML = '';

  // Create table element
  const table = document.createElement('table');
  table.id = 'sign-list';

  // Create table header row
  const headerRow = document.createElement('tr');

  // Define column headers
  const headers = ['序号','用户名', '64id','积分', '最后签到日期'];

  // Create header cells
  headers.forEach(headerText => {
    const headerCell = document.createElement('th');
    headerCell.textContent = headerText;
    headerCell.style.textAlign ='center';
    headerRow.appendChild(headerCell);
  });

  // Append header row to table
  table.appendChild(headerRow);
  // Iterate through the data and create table rows
  let index = 1;
  for (const key in data) {
    const rowData = data[key];
    const row = document.createElement('tr');

    // 序号
    const indexCell = document.createElement('td');
    indexCell.textContent = index;
    indexCell.style.textAlign = 'center';
    row.appendChild(indexCell);

    // 用户名
    const nameCell = document.createElement('td');
    nameCell.textContent = rowData.name;
    nameCell.className = 'user';
    nameCell.style.textAlign = 'center';
    row.appendChild(nameCell);

    // 设备ID
    const deviceCell = document.createElement('td');
    deviceCell.textContent = key;
    deviceCell.style.width = '150px';
    deviceCell.style.textAlign = 'center';
    row.appendChild(deviceCell);

    // 积分数
    const numberCell = document.createElement('td');
    numberCell.textContent = rowData.number;
    numberCell.className = 'number';
    numberCell.style.textAlign = 'center';
    row.appendChild(numberCell);

    // 最后签到日期
    const lastCell = document.createElement('td');
    lastCell.textContent = rowData.time;
    lastCell.className = 'last';
    lastCell.style.textAlign = 'center';
    row.appendChild(lastCell);

    // Append row to table
    table.appendChild(row);

    index++;
  }
  // Append table to container
  container.appendChild(table);
}

