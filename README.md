# wheelcar
simple kids power wheel control module


UP Board Series is a credit-card sized board with the high performance and low power consumption features of the latest tablet technology: the Intel® ATOM™ x5-Z8350 Processors 64 bits up to 1.92GHz. The internal GPU is the new Intel Gen 8 HD 400 with 12 Execution Units up to 500MHz to deliver extremely high 3D graphic performance. UP is equipped with 2GB/4GB DDR3L RAM and 16GB/32GB eMMC.

Hardware overview
UP Board Series with Intel® Atom™ x5-z8350 (up to1.92 GHz) 
Intel® HD 400 Graphics
40-pin expansion
4GB RAM
32GB Storage
Optimized Fanless Cooling Design

Compatible operating system	Microsoft Windows 10 full version

Power Requirement	5V DC-in @ 4A 5.5/2.1mm jack
Power consumption (typical)	13W
Dimension (L x W)	3.37”x 2.22” (85.6mm x 56.5mm)
USB	4 x USB2.0 port Type A
2x USB2.0 pin header
1 x USB 3.0 OTG Micro B
UART	2 x UART (Tx/Rx) debug port (pin header)
40-pin GP-bus	1


KC105 camera
c0:06:c3:ef:b8:16

IPv4 Address
192.168.1.201



UPboard computer 192.168.1.218

contorls

继电器 - control car remote

这也是一个非常常用的模块，叫做 **ESP-01/01S 继电器模块**。

关于你的问题，我有以下几个重点建议：

### 1. 这个继电器能用吗？
**能用，但是有一个巨大的限制。**
*   **物理功能上**：它的继电器部分（蓝色盒子）和你需要的完全一致，可以用来并联遥控器按钮。
*   **数量限制**：你手里只有一个继电器，而你的小车遥控器有 **4个方向（前、后、左、右）**。
    *   这个模块只能控制 **其中一个动作**（比如只能“前进”）。
    *   如果你想完全控制小车，你需要 **4个** 这样的继电器，或者买一个 **4路继电器模块**。

### 2. 用 ESP-01 能控制吗？
**非常适合！这个模块就是专门给 ESP-01 设计的。**
*   看图左上角的那个 2x4 的黑色插排，那就是给 ESP-01 插的。
*   **用法**：
    1.  把 ESP-01 插上去。
    2.  给模块供电（通常是 5V DC，接在 GND 和 VCC 端子，或者有些版本是接在排针上）。
    3.  写代码控制 ESP-01 的 **GPIO 0** 引脚。当 GPIO 0 输出低电平（或高电平，视版本而定）时，继电器就会吸合。

### 3. 用 ESP32 或 Raspberry Pi 能控制这个模块吗？
**可以，但需要用杜邦线接线。**
虽然它是给 ESP-01 设计的，但你也可以把它当成普通继电器模块用。你需要找到黑色插排上对应的引脚：

*   **VCC**：接 5V（树莓派或 ESP32 的 5V 引脚）。**注意：继电器线圈需要 5V 才能吸合，3.3V 推不动。**
*   **GND**：接 GND。
*   **GPIO0 / IO0**：这是信号引脚。接到树莓派或 ESP32 的任意 GPIO 上。

### 4. 关键避坑指南 (针对这个特定模块)
市面上这种 ESP-01 继电器模块有两个常见版本，如果你发现通电后没反应，可能是以下原因：
1.  **波特率问题**：有些旧版本不是通过 GPIO 控制的，而是通过 ESP-01 的串口发送特定 Hex 指令（如 A0 01 01 A2）来控制继电器。这比较麻烦。
2.  **GPIO0 没上拉**：有些便宜版本设计有缺陷，ESP-01 上电时 GPIO0 如果被拉低会进入“下载模式”而不是“运行模式”，导致无法启动。
3.  **最简单的方案**：如果你只是想测试一下“并联按钮”这个原理是否可行，**不用插 ESP-01**。直接用树莓派：
    *   给模块供 5V 和 GND。
    *   用一根杜邦线，一头接树莓派 GND，另一头去触碰黑色插座里的 **IO0** 脚（或者试着碰高电平），听听有没有“咔哒”声。如果有，就说明可以直接用树莓派 GPIO 控制。

### 总结建议
如果你想做完整的小车控制项目：
1.  **不要用这个模块**（除非你买4个，那样接线会很乱）。
2.  **强烈建议**买一个 **“4路 5V 继电器模块”**。
    *   这种模块一个板子上有4个继电器。
    *   用 ESP32 控制最完美（ESP32 引脚多，且自带 WiFi/蓝牙，比树莓派轻便，适合做遥控车）。
    *   ESP32 输出 3.3V 信号通常可以直接触发市面上的 5V 继电器模块（买带光耦隔离的最好）。

**下一步操作：**
你可以先拿这个模块练手，把它的输出端（绿色端子）接到遥控器的“前进”按钮上，然后用 ESP-01 或树莓派控制它吸合，体验一下通过代码让小车往前冲的感觉！