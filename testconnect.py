import RPi.GPIO as GPIO
import time

# 设置模式
GPIO.setmode(GPIO.BCM)  # 使用 BCM 编号
GPIO.setwarnings(False)

# 定义引脚 (根据上面的表格)
PIN_F = 5   # 前 (Physical 29)
PIN_B = 6   # 后 (Physical 31)
PIN_L = 13  # 左 (Physical 33)
PIN_R = 19  # 右 (Physical 35)

pins = [PIN_F, PIN_B, PIN_L, PIN_R]
names = ["前进", "后退", "左转", "右转"]

# 初始化所有引脚
for pin in pins:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.HIGH) # 初始给高电平 (继电器通常低电平触发，HIGH=断开)

print("开始测试... (按 Ctrl+C 退出)")

try:
    for i, pin in enumerate(pins):
        print(f"正在测试: {names[i]}")
        
        # 触发继电器 (如果是低电平触发)
        GPIO.output(pin, GPIO.LOW)  
        time.sleep(1) # 动1秒
        
        # 关闭继电器
        GPIO.output(pin, GPIO.HIGH) 
        time.sleep(1) # 停1秒

    print("测试完成！")

except KeyboardInterrupt:
    print("停止")

finally:
    GPIO.cleanup()