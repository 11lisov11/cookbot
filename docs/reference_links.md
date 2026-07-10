# CookBot Reference Links

Official Arduino UNO Q:

- https://docs.arduino.cc/hardware/uno-q
- https://docs.arduino.cc/resources/datasheets/ABX00162-ABX00173-datasheet.pdf
- https://docs.arduino.cc/tutorials/uno-q/user-manual/
- https://docs.arduino.cc/tutorials/uno-q/single-board-computer/
- https://docs.arduino.cc/tutorials/uno-q/debian-guide
- https://support.arduino.cc/hc/en-us/articles/23170731875740-If-your-Arduino-UNO-Q-board-software-is-out-of-date

PlatformIO:

- https://docs.platformio.org/en/stable/boards/atmelavr/megaatmega2560.html

Bluetooth and smart-home hub:

- https://www.home-assistant.io/installation/linux
- https://www.home-assistant.io/integrations/bluetooth/
- https://docs.qualcomm.com/bundle/publicresource/topics/80-80020-13
- https://www.qualcomm.com/developer/software/qualcomm-linux/support

Robot arm references:

- User AliExpress product page: https://aliexpress.ru/item/1005011788261891.html?spm=a2g2x.orderlist.0.0.75174aa6whzhc9&sku_id=12000056560392638
- Similar ProBots reference kit: https://probots.co.in/3-dof-multi-axis-programming-robotic-arm-with-quad-vacuum-suction-cups-sliding-table-unassembled-diy-kit.html
- ProBots software/library zip: https://probots.co.in/technical_data/3%20DOF%20Robotic%20Arm%20with%20Quad%20Vacuum%20Suction%20_%20Software%20%26%20library.zip
- ProBots assembly instructions zip: https://probots.co.in/technical_data/3%20DOF%20Robotic%20Arm%20with%20Quad%20Vacuum%20Suction%20_Assemly%20Instructions.zip

Gearbox references:

- FLE42 planetary gearbox family reference: https://www.jkongmotor.com/jk-fle42-planetary-gearbox.html
- FLE42-010 listing reference showing ratio 1:10 option: https://www.alibaba.com/product-detail/30arcmin-Ratio-4-1-5-1_1601028468489.html
- NEMA17 10:1 gearbox reference: https://www.omc-stepperonline.com/eg-series-planetary-gearbox-gear-ratio-10-1-backlash-15-arc-min-for-nema-17-stepper-motor-eg17-g10

Notes:

- UNO Q official docs confirm a Debian Linux MPU plus STM32 MCU architecture.
- UNO Q documentation confirms the WCBN3536A/WCN3980 Bluetooth 5.1 radio, while live deployment still checks BlueZ and kernel RFCOMM support instead of inferring it from the Bluetooth version.
- Home Assistant Container Bluetooth requires host BlueZ, the D-Bus socket, and the `NET_ADMIN`/`NET_RAW` capabilities used by the hub installer.
- The AliExpress page was not machine-readable during planning, so exact robot specs remain unconfirmed.
- ProBots is a similar reference only, not proof of the user's hardware.
- FLE42 references support the likely `010 = 10:1` interpretation, but they are not proof of the exact user-installed gearbox without the vendor datasheet.
