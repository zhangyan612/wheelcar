import mraa
import time

# 定义引脚 (Upboard GPIO 编号)
PIN_F = 5   # 前
PIN_B = 6   # 后
PIN_L = 13  # 左
PIN_R = 19  # 右

pins = [PIN_F, PIN_B, PIN_L, PIN_R]
names = ["前进", "后退", "左转", "右转"]

# 初始化所有引脚为输出模式
gpio_pins = []
for pin in pins:
    gpio = mraa.Gpio(pin)
    gpio.dir(mraa.DIR_OUT)
    gpio.write(1)  # 初始高电平 (继电器通常低电平触发，HIGH=断开)
    gpio_pins.append(gpio)

print("开始测试... (按 Ctrl+C 退出)")

try:
    for i, gpio in enumerate(gpio_pins):
        print(f"正在测试: {names[i]}")
        
        # 触发继电器 (低电平触发)
        gpio.write(0)  
        time.sleep(1) # 动1秒
        
        # 关闭继电器
        gpio.write(1) 
        time.sleep(1) # 停1秒

    print("测试完成！")

except KeyboardInterrupt:
    print("停止")

finally:
    # 关闭所有继电器
    for gpio in gpio_pins:
        gpio.write(1)