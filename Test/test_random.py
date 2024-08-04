import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

def ggl_simulation(probabilities, initial_value=1000, draw_cost=30):
    ranges = [(0, 10), (10, 25), (25, 50), (50, 80), (80, 100)] #这里粘贴数量

    max_values = []  # 存储每次抽奖的最高值
    final_values = []  # 存储每次抽奖的最终值

    current_value = initial_value

    while current_value >= draw_cost:
        # 生成随机数
        random_range = np.random.choice(len(ranges), p=probabilities)
        range_start, range_end = ranges[random_range]
        random_number = np.random.randint(range_start, range_end)

        # 扣除抽奖成本
        current_value -= draw_cost
        # 加上抽奖结果
        current_value += random_number
        # 记录每次抽奖的最高值和最终值
        max_values.append(max(current_value, initial_value))
        final_values.append(current_value)

    return max_values, final_values


def test_ggl_simulation():
    # 设置测试用例
    probabilities = [0.2, 0.65, 0.65, 0.03,0.01] #这里概率
    max_results = []  # 存储每次模拟的最高值
    final_results = []  # 存储每次模拟的最终值
    iterations = 1000  # 定义模拟次数

    # 运行模拟并记录结果
    for _ in range(iterations):
        max_values, final_values = ggl_simulation(probabilities)
        max_results.append(max(max_values))
        final_results.append(final_values[-1])  # 记录每次模拟的最终值

    # 创建包含两个子图的图形
    fig, axes = plt.subplots(1, 2, figsize=(12, 6))

    # 绘制最高值的密度图
    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # 以微软雅黑为例
    sns.kdeplot(max_results, fill=True, ax=axes[0])
    axes[0].set_title('每次抽奖时出现的最高值分布')
    axes[0].set_xlabel('最高点数')
    axes[0].set_ylabel('密度')

    # 绘制最终值的密度图
    sns.kdeplot(final_results, fill=True, ax=axes[1])
    axes[1].set_title('每次抽奖的最终值分布')
    axes[1].set_xlabel('最终点数')
    axes[1].set_ylabel('密度')

    plt.tight_layout()
    plt.show()

test_ggl_simulation()
