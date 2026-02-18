你图片中展示的是 UP Board（基于 Intel Atom x5-Z8350 的单板电脑）。虽然它是 x86 架构（和普通 PC 一样），但它的 40-pin 接口设计特意模仿了树莓派（Raspberry Pi）的布局，其电气特性兼容树莓派的扩展板。
这意味着你可以像使用树莓派一样，用它来控制继电器，进而控制那个遥控器。
以下是针对你这块板子的具体操作指南：
1. 硬件兼容性确认
电压：UP Board 的 GPIO 逻辑电平是 3.3V（虽然 CPU 是 1.8V，但板子上集成了电平转换芯片），这非常适合控制大多数继电器模块。
电源：你的继电器需要 5V 供电。UP Board 的 Pin 2 和 Pin 4 提供 5V 输出，可以直接给继电器模块供电。
接口：它的 40-pin 定义和树莓派基本一致（见你 PDF 的第 2 页 Pinout 图）。


这是一个非常关键的问题，也是新手最容易混淆的地方。

**简单回答：不需要降压。一定要用 5V 给继电器供电，同时保持遥控器的电池供电。**

这里有两个完全独立的“电源系统”，它们通过继电器实现**物理隔离**（互不干扰）。请看下面的详细解释，这对你的设备安全非常重要。

### 1. 理解“两边各论各的”

*   **左边（控制端）：继电器模块**
    *   **需求**：它的线圈（那个蓝色的方块）里面有个电磁铁，必须 **5V** 才能吸合。如果是 3V，磁力不够，它吸不动。
    *   **来源**：这个 5V 必须来自你的 **UP Board** 或者 **外部 USB 电源**。
    
*   **右边（被控端）：遥控器电路板**
    *   **需求**：它只需要 **3V**（两节7号电池）。
    *   **来源**：继续保留遥控器里的**干电池**。

### 2. 继电器到底做了什么？
继电器其实就是一个“**机械手指**”。
*   当继电器通电（5V）吸合时，它内部的金属片会“咔哒”一声连在一起。
*   这个动作，就好比你用手指去按那个黑色按钮。
*   **关键点**：继电器输出端（COM 和 NO）只是两根金属线连起来了，**它不会输出 5V 电压到遥控器上**。它只是把遥控器原本断开的线路接通了。

### 3. 接线图解（安全接法）

```text
       [ 系统 A：5V 供电 ]                      [ 系统 B：3V 供电 ]
     (你的 UP Board 或 充电头)                     (遥控器自带电池)
            │                                         │
            ▼                                         ▼
    +-------+-------+                         +-------+-------+
    |  VCC  (接5V)  | <--- 这里的电 --->      |  电池仓 (3V)  |
    |  GND  (接GND) |      完全不相通         |  电路板       |
    |  IN   (信号)  |                         |               |
    +-------+-------+                         +-------+-------+
            | 继电器模块 |                           | 遥控器按钮 |
            +-----------+                         +-----------+
            |   COM     | ----------------------- |  焊点 1   |
            |           |    (这两根线只负责      |           |
            |   NO      |     导通，不带电)       |  焊点 2   |
            +-----------+ ----------------------- +-----------+
```

### 4. 只有一种情况需要降压（你不属于这种情况）
如果你想**省掉遥控器的电池**，想直接用 UP Board 给遥控器供电，那你才需要一个降压模块（把 UP Board 的 5V 降压成 3V 接到遥控器电池仓）。

但在目前的测试阶段，**强烈建议保留遥控器电池**。这样接线最简单，也最安全。

### 总结操作：
1.  **继电器模块 VCC/GND**：接 5V 电源（让继电器能工作）。
2.  **遥控器**：装上它自己的电池（让小车能收到信号）。
3.  **连接线**：继电器的 COM/NO 接到按钮两端。

这样绝对安全，不会烧坏遥控器！你可以放心测试。

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








To access the 40-pin GPIO header on an UP Board (CHT01) running Windows using C# or C++, you must use the proprietary UP Framework and AAEON Hi-Safe drivers. Standard libraries like System.Device.Gpio often fail on standard Windows 10/11 versions without these specific vendor translations. 
1. Required Software Installation 
You cannot access the pins until the low-level hardware bridge is established:
UP Framework: Download and install the UP SDK for Windows 10/IoT. This installs the "UP Framework Service" required for GPIO communication.
Hi-Safe API: AAEON provides the Hi-Safe SDK, which includes the necessary DLLs (aaeonEapi.dll) to interface with the Digital I/O. 
AAEON
AAEON
 +3
2. Implementation in C# (Universal Windows Platform or .NET)
For C#, the most reliable method is using the UP Demo App source code as a template:
Reference DLLs: Add a reference to the aaeonEapi.dll provided in the SDK.
Import Functions: Use P/Invoke to import the GPIO control functions from the DLL.
csharp
[DllImport("aaeonEapi.dll")]
public static extern uint EApiGPIOGetDirection(uint Id, uint Bitmask, out uint pDirection);

[DllImport("aaeonEapi.dll")]
public static extern uint EApiGPIOSetLevel(uint Id, uint Bitmask, uint Level);
Use code with caution.

App Permissions: If using UWP, ensure the lowLevelDevices capability is enabled in your Package.appxmanifest. 
3. Implementation in C++
C++ development is more direct as you can link against the header files provided in the AAEON Hi-Safe SDK:
Include Headers: Use the EApi.h header found in the SDK's Include directory.
Link Library: Link your project against aaeonEapi.lib.
Example Code:
cpp
#include "EApi.h"
// Initialize the API
EApiLibInitialize();
// Set Pin 0 (mapped to Header Pin 7) to Output
EApiGPIOSetDirection(EAPI_ID_GPIO_BITMASK_0, 0xFFFFFFFF, EAPI_GPIO_LOW);
// Write High
EApiGPIOSetLevel(EAPI_ID_GPIO_BITMASK_0, 0xFFFFFFFF, EAPI_GPIO_HIGH);
Use code with caution.

4. Critical Hardware Configuration
BIOS Settings: You must often enable "HAT Configuration" in the BIOS (Advanced > HAT Configuration) and set the specific pins to "GPIO" mode rather than their alternate functions (like I2C or UART).
Pin Mapping: The software "ID" (e.g., GPIO 0) does not match the physical pin number (e.g., Pin 7). Refer to the UP-CHT01 Pinout Guide for the mapping table. 
Annabooks
Annabooks
 +1
Would you like a link to the specific pin mapping table for the 40-pin header to see which software ID corresponds to which physical pin?




undefined
undefined
undefined
11 sites
AAEON Hi-Safe
The AAEON Hi-Safe program offers a user-friendly interface to allow users ease in monitoring their devices. The AAEON Hi-Safe is a...

AAEON

UP Board Windows - UP Community
Answered 112 views 5 comments Most recent by rsramirez001 April 2023. GPIO on WinIoT Core Upboard. Answered 134 views 2 comments M...

UP Bridge the Gap

UP SDK for Windows 10 and Windows IoT - UP Shop
Up squared A1.0 A1.1 board I2C pins can't override to GPIO function. 2. Up board SPI bus not working. 3. Up squared GPIO output st...

UP-SHOP.ORG
Show all




how to run c# or c++ for gpio access on this device?
To access the 40-pin GPIO header on an UP Board (CHT01) running Windows using C# or C++, you must use the proprietary UP Framework and AAEON Hi-Safe drivers. Standard libraries like System.Device.Gpio often fail on standard Windows 10/11 versions without these specific vendor translations. 
1. Required Software Installation 
You cannot access the pins until the low-level hardware bridge is established:
UP Framework: Download and install the UP SDK for Windows 10/IoT. This installs the "UP Framework Service" required for GPIO communication.
Hi-Safe API: AAEON provides the Hi-Safe SDK, which includes the necessary DLLs (aaeonEapi.dll) to interface with the Digital I/O. 
AAEON
AAEON
 +3
2. Implementation in C# (Universal Windows Platform or .NET)
For C#, the most reliable method is using the UP Demo App source code as a template:
Reference DLLs: Add a reference to the aaeonEapi.dll provided in the SDK.
Import Functions: Use P/Invoke to import the GPIO control functions from the DLL.
csharp
[DllImport("aaeonEapi.dll")]
public static extern uint EApiGPIOGetDirection(uint Id, uint Bitmask, out uint pDirection);

[DllImport("aaeonEapi.dll")]
public static extern uint EApiGPIOSetLevel(uint Id, uint Bitmask, uint Level);
Use code with caution.

App Permissions: If using UWP, ensure the lowLevelDevices capability is enabled in your Package.appxmanifest. 
3. Implementation in C++
C++ development is more direct as you can link against the header files provided in the AAEON Hi-Safe SDK:
Include Headers: Use the EApi.h header found in the SDK's Include directory.
Link Library: Link your project against aaeonEapi.lib.
Example Code:
cpp
#include "EApi.h"
// Initialize the API
EApiLibInitialize();
// Set Pin 0 (mapped to Header Pin 7) to Output
EApiGPIOSetDirection(EAPI_ID_GPIO_BITMASK_0, 0xFFFFFFFF, EAPI_GPIO_LOW);
// Write High
EApiGPIOSetLevel(EAPI_ID_GPIO_BITMASK_0, 0xFFFFFFFF, EAPI_GPIO_HIGH);
Use code with caution.

4. Critical Hardware Configuration
BIOS Settings: You must often enable "HAT Configuration" in the BIOS (Advanced > HAT Configuration) and set the specific pins to "GPIO" mode rather than their alternate functions (like I2C or UART).
Pin Mapping: The software "ID" (e.g., GPIO 0) does not match the physical pin number (e.g., Pin 7). Refer to the UP-CHT01 Pinout Guide for the mapping table. 
Annabooks
Annabooks
 +1
Would you like a link to the specific pin mapping table for the 40-pin header to see which software ID corresponds to which physical pin?




To access the 40-pin GPIO header on an UP Board (CHT01) running Windows, install the UP SDK for Windows 10/IoT, which provides necessary drivers, documentation, and example code. Configure pin functions (GPIO/I2C/SPI/UART) in the BIOS under "Advanced" -> "HAT Configuration". For low-level control, use the RHProxy driver to enable Windows 10 IoT/Windows 10/11 GPIO mapping. 
Annabooks
Annabooks
 +2
Key Steps for Windows Access:
BIOS Setup: Upon booting, press F7 to enter the BIOS, navigate to the HAT Configuration menu, and set the desired pins (e.g., GPIO/PWM1) from PWM to GPIO.
Driver Installation: Download and install the UP SDK from the UP Community downloads page.
Software Control: Use the provided SDK examples, or access GPIO via Windows.Devices.Gpio namespace in UWP applications.
Alternative Control: Some users utilize the UP-division pinctrl driver or MRAA library for managing pin states, although this is more common on Linux. 
Annabooks
Annabooks
 +3
For detailed pin mappings and configurations, refer to the UP Board datasheet, which notes that signals pass through a Lattice FPGA, requiring the correct BIOS configuration. 



there is no Windows 10 IoT Core in image id, only have windows 8.1
If you only see Windows 8.1 (or simply "Windows") and Android in the "OS Image ID" menu, your BIOS version is outdated. The specific ACPI tables required for Windows to recognize the GPIO controller via RHPROXY were only added in later firmware updates. 
1. Update the BIOS 
To get the "Windows 10 IoT Core" option (which enables GPIO access for all Windows 10/11 versions), you must update your firmware. 
Check Current Version: Restart and press F7 to enter BIOS. Look for the version number (e.g., UPC1BM0X).
Download Latest BIOS: Visit the UP Community Downloads and download the latest UEFI BIOS (typically version v1.5 or higher for the CHT01).
Flash the BIOS: Follow the official BIOS update tutorial to create a bootable EFI shell on a USB drive and run the flash utility. 
Annabooks
Annabooks
 +1
2. Configure After Update
Once updated, the "Windows 10 IoT Core" option will appear under the Boot tab. Select it, and then:
Navigate to Advanced > HAT Configuration.
Disable the specific protocols (I2C, SPI, PWM) for the pins you want to use as GPIO.
Enable the Resource Hub Proxy (RHPROXY) if a separate toggle appears. 
Annabooks
Annabooks
 +2
3. Verify in Windows 10 Home
Standard Windows 10 Home will now see the pins:
Open Device Manager.
Look for Resource Hub Proxy Device under System Devices.
If it is there, you can now use the UP SDK for Windows to control your pins with a desktop application. 
Annabooks
Annabooks
Warning: Do not attempt to use the GPIO pins without updating the BIOS; the Windows 8.1 setting does not expose the necessary hardware addresses to the Windows 10 kernel for GPIO control. 
Super User
Super User
Would you like the direct link to the specific BIOS file for the CHT01 model?




there is no Windows 10 IoT Core in image id, only have windows 8.1
If you only see Windows 8.1 (or simply "Windows") and Android in the "OS Image ID" menu, your BIOS version is outdated. The specific ACPI tables required for Windows to recognize the GPIO controller via RHPROXY were only added in later firmware updates. 
1. Update the BIOS 
To get the "Windows 10 IoT Core" option (which enables GPIO access for all Windows 10/11 versions), you must update your firmware. 
Check Current Version: Restart and press F7 to enter BIOS. Look for the version number (e.g., UPC1BM0X).
Download Latest BIOS: Visit the UP Community Downloads and download the latest UEFI BIOS (typically version v1.5 or higher for the CHT01).
Flash the BIOS: Follow the official BIOS update tutorial to create a bootable EFI shell on a USB drive and run the flash utility. 
Annabooks
Annabooks
 +1
2. Configure After Update
Once updated, the "Windows 10 IoT Core" option will appear under the Boot tab. Select it, and then:
Navigate to Advanced > HAT Configuration.
Disable the specific protocols (I2C, SPI, PWM) for the pins you want to use as GPIO.
Enable the Resource Hub Proxy (RHPROXY) if a separate toggle appears. 
Annabooks
Annabooks
 +2
3. Verify in Windows 10 Home
Standard Windows 10 Home will now see the pins:
Open Device Manager.
Look for Resource Hub Proxy Device under System Devices.
If it is there, you can now use the UP SDK for Windows to control your pins with a desktop application. 
Annabooks
Annabooks
Warning: Do not attempt to use the GPIO pins without updating the BIOS; the Windows 8.1 setting does not expose the necessary hardware addresses to the Windows 10 kernel for GPIO control. 
Super User
Super User
Would you like the direct link to the specific BIOS file for the CHT01 model?




undefined
undefined
undefined
7 sites
Windows-10-IoT-UP2-Board-BIOS-RHPROXY ... - Annabooks
Since Windows 10 IoT Core and Windows 10 Enterprise LTSC 2019 (aka Windows 10 IoT Enterprise) are the same operating system, the s...

Annabooks

UP Board Firmware Settings to Enable SPI/I2C/GPIO/UART for ...
The second step is to configure the GPIO. In the Advanced-> HAT, Configuration-> GPIO Configuration In Pin Order, you can set any ...

Annabooks

BIOS Does not have "Windows 10 IOT Core" option
Nov 16, 2018 — BIOS Does not have "Windows 10 IOT Core" option — upcommunity. Home › UP Product Related Discussions › UP Squared › UP Squared Win...

UP Bridge the Gap
Show all
is there any other options？
If you cannot update the BIOS or the "Windows 10 IoT Core" option is missing, your options for accessing the 40-pin header on Windows 10 Home are limited because the hardware is not exposed to the operating system's standard driver stack. 
Annabooks
Annabooks
 +1
Here are the remaining alternatives:
1. Manual Driver Installation (Aaeon/UP SDK)
Even without the specific BIOS toggle, you can try to manually force the installation of the manufacturer's drivers.
Download: The UP Board Windows 10 64-bit driver package.
Manual Install: Open Device Manager, find any "Unknown Devices" (likely listed with IDs like AAEON_DEV_081C or similar), and manually point the "Update Driver" browse tool to the unzipped driver folder.
Access: If successful, use the UP SDK which provides the aaeonEapi.dll library to interact with the pins through C# or C++. 
2. External USB-to-GPIO Adapter
If the onboard header remains inaccessible due to the old BIOS, the most reliable "workaround" for Windows 10 Home is an external bridge.
FT232H Breakout: Devices like the Adafruit FT232H connect via USB and provide GPIO, SPI, and I2C pins that are natively supported on Windows via Python libraries (e.g., Adafruit_Blinka).
Arduino/Microcontroller: Use an Arduino (connected via USB) as a dedicated I/O controller, communicating with your Windows app over a Serial/COM port. 
YouTube
YouTube
 +3
3. Switch to Linux (Dual Boot or Live USB)
The GPIO pins on the CHT01 are significantly easier to access on Linux because you can use a custom kernel that doesn't rely on the BIOS-to-Windows RHPROXY bridge. 
RobotExchange
RobotExchange
 +1
You can boot Ubuntu from a USB stick and install the upboard-extras package to gain immediate control of the 40-pin header. 
GitHub Pages documentation
GitHub Pages documentation
Summary of Limitations
Method	Complexity	Reliability on Home Edition
BIOS Update	Medium	High (Standard method)
Manual Driver Force	High	Medium (Depends on ACPI tables)
USB-to-GPIO Bridge	Low	High (Bypasses BIOS/Driver issues)
Switch to Linux	Low	High (Bypasses Windows limitations)
Important Note: Direct register access (bit-banging) is not recommended on Windows because the OS manages hardware addresses behind a protection layer; without the driver being active, your application will likely crash with an access violation if it tries to touch the GPIO memory addresses directly. 
These technical forum posts discuss native C libraries for GPIO access and interacting with GPIO on Windows 10 for non-Raspberry Pi devices:
Native C libraries to GPIO pins? - Community Forum
Sep 15, 2016 — Comments. Dan O'Donovan Administrator, Moderator, Emutex Posts: 241 admin. September 2016. For a native C library, I suggest using...

UP Bridge the Gap
How to communicate with GPIO on windows (Win 10) for non ...
May 15, 2019 — You cannot use BIOS interrupts when the CPU is in protected mode, which all modern operating systems use. Looking at the manual fo...

Stack Overflow

UpBoard Configuration - UpCluster - GitHub Pages
Install the upboard-extras. sudo apt install upboard-extras. Add the user that needs to access the HAT funcionality. GPIO. sudo us...

GitHub Pages documentation
GPIO/I2C kernel support for UP2 board, taken from https://aur ...
You only strictly need to install the core kernel and modules: $ cd .. $ sudo dpkg -i linux-image-unsigned-4.15.0-40-generic_4.15.

Gist

[Solved] Controling GPIO pins on upboard with Python/Ubuntu
Jun 11, 2018 — The problem with these board is that the GPIO pins can't handle much current. For the UP board this is max. 24 mA (see: Pinout · u...

RobotExchange

Add Python programmable GPIO pins to any computer with ...
Jun 5, 2024 — i've got a lot of development boards for a variety of purposes. and this is just a few of them because sometimes I don't want to y...

YouTube·Nick Bild

3:54
Would you like the pin-out diagram for the CHT01 to help you identify which pins to use if you try the manual driver method?

