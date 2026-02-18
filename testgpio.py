import time
import os

# 定义引脚 (Upboard GPIO 编号)
PIN_F = 5   # 前
PIN_B = 6   # 后
PIN_L = 13  # 左
PIN_R = 19  # 右

pins = [PIN_F, PIN_B, PIN_L, PIN_R]
names = ["前进", "后退", "左转", "右转"]

GPIO_PATH = "/sys/class/gpio"

def export_pin(pin):
    """导出 GPIO 引脚"""
    if not os.path.exists(f"{GPIO_PATH}/gpio{pin}"):
        with open(f"{GPIO_PATH}/export", "w") as f:
            f.write(str(pin))
        time.sleep(0.1)  # 等待系统创建目录

def unexport_pin(pin):
    """取消导出 GPIO 引脚"""
    if os.path.exists(f"{GPIO_PATH}/gpio{pin}"):
        with open(f"{GPIO_PATH}/unexport", "w") as f:
            f.write(str(pin))

def set_direction(pin, direction):
    """设置引脚方向 (out/in)"""
    with open(f"{GPIO_PATH}/gpio{pin}/direction", "w") as f:
        f.write(direction)

def write_pin(pin, value):
    """写入引脚值 (0/1)"""
    with open(f"{GPIO_PATH}/gpio{pin}/value", "w") as f:
        f.write(str(value))

# 初始化所有引脚为输出模式
for pin in pins:
    export_pin(pin)
    set_direction(pin, "out")
    write_pin(pin, 1)  # 初始高电平 (继电器通常低电平触发，HIGH=断开)

print("开始测试... (按 Ctrl+C 退出)")

try:
    for i, pin in enumerate(pins):
        print(f"正在测试: {names[i]}")
        
        # 触发继电器 (低电平触发)
        write_pin(pin, 0)  
        time.sleep(1) # 动1秒
        
        # 关闭继电器
        write_pin(pin, 1) 
        time.sleep(1) # 停1秒

    print("测试完成！")

except KeyboardInterrupt:
    print("停止")

finally:
    # 关闭所有继电器并清理
    for pin in pins:
        write_pin(pin, 1)
        unexport_pin(pin)