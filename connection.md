祝贺你！4个继电器都接好了，最难的物理连接部分已经完成。

现在的挑战是：**UP Board 上的 5V 电源引脚很少（只有2个），但你有4个继电器需要供电。**

你需要做一个**“并联供电”**，并分配**信号线**。

### 1. 电源线怎么接（VCC 和 GND）

由于继电器模块需要 5V，而 UP Board 上只有 **Pin 2**和 **Pin 4** 是 5V。你不能把4根线硬塞进一个孔里。

**你需要把4个继电器的电源线“汇聚”到一起。**

#### 方案 A：如果你有面包板 (推荐)
1.  从 UP Board **Pin 2 (5V)** 接一根线到面包板的 **红线区 (+) **。
2.  从 UP Board **Pin 6 (GND)** 接一根线到面包板的 **蓝线区 (-) **。
3.  把 4个继电器的 **VCC** 都插到面包板 **红线区**。
4.  把 4个继电器的 **GND** 都插到面包板 **蓝线区**。

#### 方案 B：如果没有面包板 (手拧法)
你需要把线拧在一起（类似做一种“一分四”的线）：
1.  **VCC (5V)**: 把 4个继电器的 VCC 线头剥开，拧在一起，再焊接到一根主线上（或者缠紧用胶带包好），这根主线插到 UP Board 的 **Pin 2**。
2.  **GND (地)**: UP Board 上有很多 GND 引脚 (**Pin 6, 9, 14, 20, 25, 30, 34, 39**)。
    *   你可以把 4个继电器的 GND 分别插到这些不同的 GND 引脚上，不用非要拧在一起。这样比较方便。

---

### 2. 信号线怎么接 (GPIO 控制线)

你需要把每个继电器的 **控制脚 (GPIO0 / IN)** 接到 UP Board 不同的 GPIO 引脚上。

为了方便写程序，我们选用这一组挨得比较近的引脚（兼容树莓派定义）：

| 动作 | 继电器端 | UP Board 物理引脚 (Physical) | BCM 编号 (写代码用) |
| :--- | :--- | :--- | :--- |
| **前进 (Forward)** | IO0 / IN | **Pin 29** | GPIO 5 |
| **后退 (Back)** | IO0 / IN | **Pin 31** | GPIO 6 |
| **左转 (Left)** | IO0 / IN | **Pin 33** | GPIO 13 |
| **右转 (Right)** | IO0 / IN | **Pin 35** | GPIO 19 |
| *(备选 GND)* | GND | **Pin 39** | - |

*(注：我选这几个脚是因为它们聚在一起，而且避开了 I2C/UART 等常用功能脚，比较单纯)*

---

### 3. 接线总结图

请按照这个逻辑检查你的连线：

*   **UP Board Pin 2 (5V)** ---> 分成4路 ---> 接所有继电器的 **VCC**
*   **UP Board GND (Pin 6/9/14/20)** ---> 接所有继电器的 **GND**
*   **UP Board Pin 29** ---> 接 **前进** 继电器的 **IO0**
*   **UP Board Pin 31** ---> 接 **后退** 继电器的 **IO0**
*   **UP Board Pin 33** ---> 接 **左转** 继电器的 **IO0**
*   **UP Board Pin 35** ---> 接 **右转** 继电器的 **IO0**

---

### 4. 简单的测试代码 (Python)

接好线后，用这段代码测试一下所有方向。记得先安装好 UP Board 的 GPIO 库（参考之前的步骤）。

```python
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
```

**特别注意：**
你的 ESP-01 继电器模块通常是 **低电平触发 (Active LOW)**。
*   如果运行代码时，继电器**一开始就全部吸合**了，那就说明它是**高电平触发**。
*   如果是这样，你需要把代码里的 `GPIO.HIGH` 和 `GPIO.LOW` 互换一下。

先去接电源线吧，如果线太乱，记得用胶带捆一下，别让正负极碰到一起短路了！