Ты опытный robotics / embedded Linux / Arduino / AI-agent разработчик. Нужно создать программное обеспечение для робота-повара CookBot на базе Arduino UNO Q + Arduino Mega + роботизированной arm-руки с AliExpress.

# Project Identity

Project name: CookBot
Full name: CookBot Robot Cook Assistant
Repository name: cookbot_unoq_mega
App name: CookBot
PWA display name: CookBot
PWA short name: CookBot
Backend service name: cookbot-backend
Fake Mega service name: cookbot-fake-mega
Arduino Mega firmware name: cookbot_mega_firmware

Везде в коде, README, документации, UI, PWA manifest, service files, логах, API title и комментариях использовать название CookBot.
Не использовать generic names вроде robot_arm_unoq_mega, robot_cook_unoq_mega, UNO Q Robot Cook, Robot Arm Controller.

# Reference Documentation

Перед проектированием и генерацией кода изучи и используй эти источники как технические reference links:

1. Arduino UNO Q official documentation:
https://docs.arduino.cc/hardware/uno-q

2. Arduino UNO Q User Manual:
https://docs.arduino.cc/tutorials/uno-q/user-manual/

3. Arduino UNO Q as Single-Board Computer:
https://docs.arduino.cc/tutorials/uno-q/single-board-computer/

4. Arduino UNO Q Debian Linux basics:
https://docs.arduino.cc/tutorials/uno-q/debian-guide

5. User's robot product page:
https://aliexpress.ru/item/1005011788261891.html?spm=a2g2x.orderlist.0.0.75174aa6whzhc9&sku_id=12000056560392638

6. Similar/reference robotic arm kit with Mega/RAMPS:
https://probots.co.in/3-dof-multi-axis-programming-robotic-arm-with-quad-vacuum-suction-cups-sliding-table-unassembled-diy-kit.html

7. Reference software/library download from similar arm kit:
https://probots.co.in/technical_data/3%20DOF%20Robotic%20Arm%20with%20Quad%20Vacuum%20Suction%20_%20Software%20%26%20library.zip

8. Reference assembly instructions download from similar arm kit:
https://probots.co.in/technical_data/3%20DOF%20Robotic%20Arm%20with%20Quad%20Vacuum%20Suction%20_Assemly%20Instructions.zip

Правила работы с документацией:
- Не выдумывать точные характеристики робота, если они не подтверждены документацией.
- Не выдумывать количество осей, распиновку, тип драйверов, размеры звеньев, передаточные числа, лимиты и токи.
- Если данных нет, использовать конфиги, safe defaults, homing, calibration wizard и docs/vendor_robot_notes.md.
- Если документация товара противоречит фактическому железу пользователя, приоритет имеет фактическое железо пользователя.
- Если robot docs недоступны, проект всё равно должен работать в no-hardware mode через simulator/fake_mega/mock_camera/mock_ai.

# Главная идея проекта

- Arduino UNO Q = верхний контроллер, оркестратор, веб-сервер, камера, AI/GPT API, VPN, safety layer, recipe engine, мобильное приложение.
- Arduino Mega = низкоуровневый контроллер руки, двигателей/сервоприводов, концевиков, homing, watchdog, emergency stop.
- Телефон = управление роботом через мобильное PWA-приложение в тёмной теме.
- AI/GPT = планировщик и помощник, но не прямой водитель моторов.
- CookBot = recipe-controlled robot cook workflow, а не произвольная автономная магия.

# Важные ограничения

- Arduino Mega остаётся в проекте и управляет рукой.
- Arduino UNO Q не управляет сервоприводами напрямую в MVP.
- Arduino UNO Q общается с Arduino Mega по USB Serial или UART.
- AI/GPT не имеет прямого доступа к сервоприводам, двигателям, нагреву или опасным действиям.
- AI может только предложить план в строгом JSON.
- UNO Q safety layer обязан проверить каждый шаг.
- Arduino Mega дополнительно проверяет лимиты, концевики, watchdog и ESTOP.
- При любой ошибке AI, API, камеры, VPN, Wi-Fi, backend или связи с Mega движение запрещается.
- Разработка должна полностью тестироваться без реального железа через simulator, fake_mega, mock_camera и mock_ai.

# Текущее железо

- Arduino UNO Q.
- Arduino Mega.
- Роботизированная arm-рука с AliExpress.
- Камера подключается к Arduino UNO Q.
- Телефон управляет системой через мобильное PWA-приложение.
- Есть одна насадка: хвататель / gripper.
- Сменных насадок нет.
- Датчиков абсолютного положения, энкодеров и force/torque sensor нет.
- Есть только концевики на двигателях/осях.

Концевики используются для:
- homing;
- определения крайних положений;
- аварийной остановки движения в сторону предела;
- проверки, что ось дошла до края при калибровке;
- обнаружения ошибки движения.

Концевики НЕ являются полноценными датчиками положения. Если нет энкодеров, система не должна притворяться, что знает точную фактическую позицию. Система знает только commanded position, home state, calibration state и состояние концевиков. Если позиция могла быть потеряна, система должна требовать re-home. После ручного перемещения руки при выключенном питании, ESTOP, застревания, ошибки концевика или сбоя связи требуется re-home или подтверждённая диагностика.

# Питание и безопасность железа

- Двигатели/сервоприводы питаются только от отдельного источника питания.
- Нельзя питать двигатели/сервоприводы от 5V пина Arduino.
- GND питания двигателей, Arduino Mega и UNO Q должны быть общими.
- Servo/motor power должен иметь предохранитель.
- Желательно добавить аппаратный выключатель питания сервоприводов/двигателей.
- ESTOP должен аппаратно отключать питание двигателей/сервоприводов или подавать запрет движения на Mega.
- Mega не должна подавать движение до ENABLE_MOTION.
- При старте не должно быть резкого рывка.
- Все движения должны быть плавными.
- При timeout связи Mega останавливает движение.
- При ESTOP Mega отключает servo output, если возможно.

# Цель проекта

Создать полноценный проект-репозиторий CookBot:
1. Управление рукой с телефона.
2. Мобильное PWA-приложение в тёмной теме.
3. Просмотр камеры с телефона.
4. Ручное управление рукой.
5. Homing по концевикам.
6. Калибровка осей.
7. Голосовые и текстовые команды.
8. AI-режим через OpenAI-compatible API, например GPT API.
9. Передача snapshot изображения с камеры в AI.
10. Recipe Engine для пошаговых рецептов.
11. Безопасный исполнитель команд.
12. VPN split-tunnel для связи с AI API, чтобы локальный Wi-Fi не ломался.
13. Simulator mode и fake Mega для тестов без железа.
14. Полный no-hardware тестовый цикл до прохождения acceptance criteria.

# Архитектура

## Телефон
- Открывает мобильное PWA-приложение CookBot в браузере.
- Интерфейс mobile-first.
- Основная тема: тёмная / night mode.
- Пользователь видит камеру.
- Пользователь управляет рукой вручную.
- Пользователь запускает homing.
- Пользователь выполняет calibration.
- Пользователь отправляет текстовые или голосовые команды.
- Пользователь запускает AI-режим.
- Пользователь запускает рецепты.
- Пользователь видит статус UNO Q, Mega, камеры, VPN, AI, ESTOP, homing, calibration, концевиков.
- Кнопка Emergency Stop всегда видна и доступна одним нажатием.

## Arduino UNO Q
Linux/Debian-side:
- FastAPI backend;
- Web/PWA server;
- WebSocket для состояния системы;
- camera stream;
- AI client;
- vision snapshot;
- safety layer;
- recipe engine;
- kitchen workspace model;
- serial protocol master для Arduino Mega;
- VPN split-tunnel;
- structured logging.

STM32-side UNO Q:
- В MVP не используется для управления рукой.
- Можно оставить как optional GPIO/ESTOP bridge.
- Основной исполнитель руки: Arduino Mega.

## Arduino Mega
- Принимает команды от UNO Q по Serial/UART.
- Управляет сервоприводами/двигателями руки.
- Читает концевики.
- Выполняет homing.
- Проверяет min/max software limits.
- Проверяет limit switches.
- Проверяет max speed.
- Поддерживает HOME.
- Поддерживает ESTOP.
- Поддерживает watchdog.
- При потере связи с UNO Q останавливает движение.
- Никогда не выполняет команды вне лимитов.
- Никогда не двигает ось дальше, если сработал соответствующий концевик.

# Этапы разработки

MVP-1:
- UNO Q запускает backend.
- Телефон открывает PWA в тёмной теме.
- Камера показывает поток или mock stream.
- UNO Q видит Arduino Mega по Serial или fake_mega.
- Mega/fake_mega отвечает на hello/ping/get_state.
- Работает simulator mode.
- Работает fake_mega mode.
- Работает ESTOP.
- Можно двигать один сустав/ось вручную в симуляции.

MVP-2:
- Управление всеми осями.
- Управление gripper.
- Чтение концевиков.
- Homing.
- Калибровка.
- Сохранение arm_config.yaml.
- Ограничения углов/скоростей.
- Real motion запрещён без homing/calibration.

MVP-3:
- AI text command.
- AI возвращает только JSON.
- Safety layer проверяет JSON.
- Опасные команды отклоняются.
- AI не может напрямую управлять Mega.

MVP-4:
- Recipe Engine без нагрева.
- Тестовые рецепты с холодными безопасными объектами.
- Перемешивание холодных ингредиентов.
- Перемещение лёгких безопасных предметов.

MVP-5:
- Supervised cooking mode.
- Только под наблюдением пользователя.
- Только после preflight checklist.
- Без автоматического управления горячими объектами, если нет датчика температуры и безопасного appliance interface.

# Системные режимы

manual_mode:
- пользователь вручную двигает рукой;
- все команды проходят через UNO Q safety layer и Mega safety.

assistant_mode:
- робот работает только с холодными, лёгкими, безопасными объектами;
- запрещены горячие предметы, плита, ножи, стекло, тяжёлые предметы, масло, кипяток.

recipe_mode:
- робот выполняет только заранее утверждённые рецепты;
- AI не может генерировать произвольные движения;
- AI может выбрать рецепт, объяснить план и запросить подтверждение;
- каждый шаг рецепта проходит safety validation.

supervised_cooking_mode:
- разрешены только ограниченные кухонные операции;
- пользователь должен подтвердить начало;
- камера должна работать;
- ESTOP должен быть доступен;
- Mega должна отвечать;
- рука должна быть homed и calibrated;
- зона движения должна быть свободна;
- без датчика температуры запрещены действия, где робот сам решает, что горячий объект безопасен.

advanced_kitchen_lab_mode:
- выключен по умолчанию;
- включается только в конфиге;
- требует preflight checklist;
- требует подтверждение пользователя;
- используется для экспериментальных задач вроде "приготовь яичницу";
- не должен включаться автоматически;
- запрещает автономную работу без наблюдения.

# State Machine

Добавить явную машину состояний:

- BOOTING
- SIMULATOR_READY
- MEGA_DISCONNECTED
- MEGA_CONNECTED
- NOT_HOMED
- NOT_CALIBRATED
- HOMING
- CALIBRATION_MODE
- IDLE_SAFE
- MANUAL_CONTROL
- AI_PLANNING
- WAITING_USER_CONFIRMATION
- EXECUTING_COMMAND
- EXECUTING_RECIPE
- PAUSED
- ESTOP_ACTIVE
- ERROR_LOCKED

Правила:
- Из ESTOP_ACTIVE нельзя перейти сразу в EXECUTING_COMMAND.
- После ESTOP требуется CLEAR_ESTOP, проверка Mega, проверка концевиков, проверка конфигурации и возврат в IDLE_SAFE.
- Если Mega disconnected, все движения запрещены.
- Если camera unavailable, AI motion запрещён.
- Если NOT_HOMED, real motion запрещён кроме homing/calibration.
- Если NOT_CALIBRATED, real motion запрещён кроме calibration.
- Если recipe executing, manual motion запрещён кроме STOP/ESTOP.
- Любая ошибка safety переводит систему в ERROR_LOCKED или IDLE_SAFE.
- Если сработал концевик во время движения не в режиме homing, движение останавливается и система требует диагностики.

# Концевики и homing

Добавить поддержку limit switches.

configs/limits_config.yaml:
limit_switches:
  enabled: true
  axes:
    - axis_id: 0
      name: "base"
      min_switch_pin: 22
      max_switch_pin: 23
      active_low: true
      debounce_ms: 30
    - axis_id: 1
      name: "shoulder"
      min_switch_pin: 24
      max_switch_pin: 25
      active_low: true
      debounce_ms: 30
    - axis_id: 2
      name: "elbow"
      min_switch_pin: 26
      max_switch_pin: 27
      active_low: true
      debounce_ms: 30
    - axis_id: 3
      name: "wrist"
      min_switch_pin: 28
      max_switch_pin: 29
      active_low: true
      debounce_ms: 30
    - axis_id: 4
      name: "wrist_rotate"
      min_switch_pin: 30
      max_switch_pin: 31
      active_low: true
      debounce_ms: 30

Homing:
- Каждая ось медленно движется к home/min концевику.
- После срабатывания концевика движение останавливается.
- Ось немного отъезжает назад.
- Состояние оси помечается как homed.
- После homing commanded_position сбрасывается в известное значение.
- Если концевик не сработал за timeout, homing failed.
- Если концевик уже активен при старте, ось должна аккуратно отъехать или запросить ручную проверку.
- Если концевики отсутствуют на части осей, это должно быть указано в конфиге.

# Связь UNO Q ↔ Arduino Mega

Использовать USB Serial как основной вариант.
Скорость: 115200 или 500000 baud, параметр в config.
Протокол: line-based JSONL.
Каждая команда — одна JSON-строка.
Каждый ответ — одна JSON-строка.
Все команды имеют id, timestamp, type, payload.
Mega отвечает ack/error/state.

HELLO command:
{
  "id": "cmd_001",
  "type": "hello",
  "protocol_version": "1.0",
  "client": "cookbot_backend",
  "capabilities": ["set_joint", "set_joints", "gripper", "estop", "state", "home", "read_limits"]
}

Mega response:
{
  "id": "cmd_001",
  "ok": true,
  "protocol_version": "1.0",
  "firmware": "cookbot_mega_firmware",
  "firmware_version": "0.1.0",
  "capabilities": ["set_joint", "set_joints", "gripper", "estop", "watchdog", "limit_switches", "homing"]
}

Типы команд UNO Q → Mega:
- hello
- ping
- get_state
- read_limit_switches
- home_axis
- home_all
- set_joint
- set_joints
- jog_axis
- stop_motion
- move_home
- gripper_open
- gripper_close
- gripper_set
- estop
- clear_estop
- enable_motion
- disable_motion
- set_speed_limit

Типы ошибок Mega:
- invalid_json
- unknown_command
- incompatible_protocol
- angle_limit
- speed_limit
- limit_switch_active
- not_homed
- not_calibrated
- estop_active
- watchdog_timeout
- servo_fault
- homing_failed
- motion_disabled

# Структура проекта

cookbot_unoq_mega/
  README.md
  Makefile
  .gitignore
  docs/
    architecture.md
    wiring.md
    safety.md
    calibration.md
    homing_and_limits.md
    ai_mode.md
    robot_cook_architecture.md
    kitchen_station.md
    recipe_format.md
    food_safety.md
    vpn_split_tunnel.md
    first_start.md
    no_hardware_testing.md
    reference_links.md
    vendor_robot_notes.md
  configs/
    arm_config.yaml
    limits_config.yaml
    gripper_config.yaml
    kitchen_workspace.yaml
    ai_config.example.yaml
    serial_config.yaml
    vpn_config.example.yaml
  recipes/
    test_recipe.yaml
    stir_cold_ingredients.yaml
    move_safe_object.yaml
    supervised_scrambled_eggs.locked_example.yaml
  unoq_backend/
    main.py
    requirements.txt
    app/
      server.py
      config.py
      state.py
      logger.py
      state_machine.py
      routes/
        health.py
        control.py
        camera.py
        ai.py
        calibration.py
        homing.py
        recipes.py
        system.py
        logs.py
      serial_bridge/
        mega_protocol.py
        mega_client.py
        command_queue.py
        watchdog.py
        fake_mega_client.py
      robot/
        safety.py
        motion_planner.py
        kinematics.py
        executor.py
        simulator.py
        command_models.py
        limit_switches.py
      kitchen/
        recipe_engine.py
        recipe_models.py
        recipe_executor.py
        kitchen_safety.py
        workspace_model.py
        preflight_check.py
        ingredient_tracker.py
        appliance_controller.py
      vision/
        camera.py
        stream_mjpeg.py
        snapshot.py
        object_detection_stub.py
        camera_calibration.py
        mock_camera.py
      ai/
        llm_client.py
        mock_ai_client.py
        prompt_builder.py
        schemas.py
        command_parser.py
        policy.py
      voice/
        speech_to_text.py
        text_to_speech.py
      vpn/
        split_tunnel.py
        route_check.py
  mega_firmware/
    cookbot_mega_firmware/
      cookbot_mega_firmware.ino
      Config.h
      Protocol.h
      Protocol.cpp
      ServoDriver.h
      ServoDriver.cpp
      LimitSwitches.h
      LimitSwitches.cpp
      Homing.h
      Homing.cpp
      Safety.h
      Safety.cpp
      Motion.h
      Motion.cpp
      Watchdog.h
      Watchdog.cpp
  web_app/
    package.json
    vite.config.js
    index.html
    public/
      manifest.webmanifest
      icons/
        icon-192.png
        icon-512.png
    src/
      main.jsx
      App.jsx
      api.js
      websocket.js
      styles/
        theme.css
        layout.css
      components/
        CameraView.jsx
        EmergencyStop.jsx
        StatusPanel.jsx
        ManualControl.jsx
        JointSlider.jsx
        GripperControl.jsx
        AiCommandPanel.jsx
        VoiceCommand.jsx
        CalibrationPanel.jsx
        HomingPanel.jsx
        RecipePanel.jsx
        PreflightPanel.jsx
        SettingsPanel.jsx
        LogPanel.jsx
        ConfirmDialog.jsx
      pages/
        Dashboard.jsx
        CameraPage.jsx
        ManualPage.jsx
        AiPage.jsx
        RecipesPage.jsx
        CalibrationPage.jsx
        HomingPage.jsx
        SettingsPage.jsx
  scripts/
    install_unoq.sh
    run_backend.sh
    run_web_dev.sh
    setup_systemd.sh
    setup_vpn_split_tunnel.sh
    run_fake_mega.sh
    check_all.sh
    flash_mega_notes.md
  tests/
    test_safety.py
    test_state_machine.py
    test_mega_protocol.py
    test_limit_switches.py
    test_ai_schema.py
    test_executor.py
    test_recipe_engine.py
    test_simulator.py
    test_fake_mega.py
    test_mock_camera.py
    test_mock_ai.py

# Backend UNO Q

Использовать:
- Python 3.
- FastAPI.
- Uvicorn.
- pyserial.
- OpenCV.
- Pydantic.
- python-dotenv.
- PyYAML.
- WebSocket.
- MJPEG camera stream.

REST endpoints:
- GET /health
- GET /state
- GET /config
- POST /control/joint
- POST /control/joints
- POST /control/jog
- POST /control/gripper
- POST /control/home
- POST /control/stop
- POST /control/estop
- POST /control/clear-estop
- POST /homing/axis
- POST /homing/all
- GET /limits/state
- GET /camera/stream
- POST /camera/snapshot
- POST /ai/command
- POST /ai/voice-command
- GET /recipes
- POST /recipes/start
- POST /recipes/pause
- POST /recipes/abort
- POST /calibration/start
- POST /calibration/set-joint
- POST /calibration/save
- GET /logs/recent
- GET /logs/download

WebSocket:
- /ws/state

# Конфиги

configs/arm_config.yaml должен содержать:
robot:
  name: "cookbot_arm_mega"
  dof_count: 5
  calibrated: false
  homed: false
  simulator: true
  robot_enabled: false
  end_effector: "single_gripper"

serial:
  port: "/dev/ttyACM0"
  baudrate: 115200
  timeout_s: 1.0
  watchdog_ms: 500

joints:
  - id: 0
    name: "base"
    channel: 0
    min_angle: 20
    max_angle: 160
    home_angle: 90
    max_speed_deg_s: 20
    inverted: false
    requires_homing: true
  - id: 1
    name: "shoulder"
    channel: 1
    min_angle: 30
    max_angle: 150
    home_angle: 90
    max_speed_deg_s: 15
    inverted: false
    requires_homing: true
  - id: 2
    name: "elbow"
    channel: 2
    min_angle: 30
    max_angle: 150
    home_angle: 90
    max_speed_deg_s: 15
    inverted: false
    requires_homing: true
  - id: 3
    name: "wrist"
    channel: 3
    min_angle: 20
    max_angle: 160
    home_angle: 90
    max_speed_deg_s: 20
    inverted: false
    requires_homing: true
  - id: 4
    name: "wrist_rotate"
    channel: 4
    min_angle: 20
    max_angle: 160
    home_angle: 90
    max_speed_deg_s: 20
    inverted: false
    requires_homing: true

gripper:
  id: 5
  channel: 5
  type: "single_gripper"
  open_angle: 30
  close_angle: 90
  safe_close_angle: 70
  max_speed_deg_s: 10
  food_safe: false
  heat_safe: false

safety:
  require_homing_before_real_motion: true
  require_calibration_before_real_motion: true
  robot_enabled_by_default: false
  max_command_queue: 3
  forbid_hot_objects: true
  forbid_food_cooking_without_supervision: true
  forbid_knives: true
  forbid_glass: true
  forbid_heavy_objects: true
  forbid_open_flame: true
  require_confirmation_for_medium_risk: true
  require_confirmation_for_high_risk: true
  require_camera_for_ai_motion: true
  require_workspace_clear_confirmation: true

camera:
  device: "/dev/video0"
  width: 640
  height: 480
  fps: 15
  ai_snapshot_width: 512
  ai_snapshot_height: 384
  mock_camera_if_missing: true

configs/kitchen_workspace.yaml:
workspace:
  coordinate_system: "table_relative"
  calibrated: false
  robot_base_position: null
  safe_zones: []
  forbidden_zones:
    - name: "unknown_area"
      description: "All unknown areas are forbidden until calibrated"
  stove_zone:
    enabled: false
    requires_supervised_mode: true
  human_interaction_zone:
    requires_workspace_clear_confirmation: true
  ingredient_zones: []
  bowl_positions: []
  pan_position: null
  camera_calibration:
    calibrated: false

configs/gripper_config.yaml:
end_effector:
  id: "single_gripper"
  type: "gripper"
  installed: true
  food_safe: false
  heat_safe: false
  allowed_actions:
    - grip_light_object
    - move_cold_object
    - hold_spoon_if_manually_inserted
    - simple_stir_cold
  forbidden_actions:
    - touch_hot_pan
    - touch_food_directly_if_not_food_safe
    - hold_knife
    - lift_heavy_pan
    - handle_glass
    - handle_boiling_water

# Camera and workspace calibration

Добавить процедуру калибровки камеры и рабочей поверхности:
- workspace homography для плоской поверхности;
- calibration target mode;
- сопоставление camera pixel -> workspace coordinate;
- сохранение calibration data в configs/camera_calibration.yaml.

Если camera calibration отсутствует:
- AI может описывать сцену;
- AI может предложить ручное управление;
- AI не может отдавать move_to_object;
- робот может выполнять только manual mode или predefined recipe positions.

# Одна насадка / gripper

- Не реализовывать систему сменных инструментов.
- Не требовать tool changer.
- Считать, что установлен один постоянный gripper.
- Если gripper не food_safe, робот не должен касаться еды напрямую.
- Если gripper не heat_safe, робот не должен работать с горячей сковородкой.
- Для тестов разрешены только холодные безопасные предметы.
- Для перемешивания можно использовать ложку/лопатку, если пользователь вручную закрепил её в gripper и подтвердил это в UI.

# Sensors

Текущие датчики:
- camera_status;
- mega_connection;
- estop_status;
- limit_switches;
- servo_power_status optional.

Нет:
- absolute position sensors;
- encoders;
- force/torque sensor;
- automatic tool detection;
- automatic temperature sensor, unless later added.

# Simulator and Fake Mega

software_simulator:
- backend не открывает serial port;
- состояние руки хранится в Python;
- команды меняют виртуальные углы;
- limit switches можно имитировать;
- gripper можно имитировать;
- homing можно имитировать.

fake_mega:
- отдельный Python-процесс или класс;
- эмулирует Arduino Mega JSONL protocol;
- поддерживает hello, ping, get_state, set_joint, set_joints, jog_axis, home_axis, home_all, gripper_open, gripper_close, estop, clear_estop;
- умеет имитировать концевики;
- умеет имитировать homing;
- умеет имитировать ошибки timeout, invalid_json, angle_limit, speed_limit, limit_switch_active, not_homed, estop_active, homing_failed, mega_disconnected.

mock_camera:
- если /dev/video0 недоступна, backend должен использовать тестовое изображение;
- camera stream должен показывать mock frame;
- snapshot endpoint должен возвращать mock snapshot;
- UI должен работать даже без реальной камеры.

mock_ai_client:
- не требует реального AI_API_KEY;
- если AI_API_KEY отсутствует, backend использует mock AI;
- mock AI возвращает валидные JSON-ответы;
- mock AI принимает безопасную команду;
- mock AI отклоняет "приготовь яичницу", "возьми нож", "переставь горячую сковородку";
- mock AI запрашивает уточнение, если объект неизвестен.

# Mobile PWA

Сделать mobile-first PWA-приложение для телефона в тёмной теме.

Требования:
- Основная тема: dark / night mode.
- Фон тёмный.
- Крупные кнопки под палец.
- Адаптация под вертикальный экран телефона.
- Android Chrome как основной target.
- iOS Safari как secondary target.
- Emergency Stop всегда закреплён поверх интерфейса.
- Emergency Stop красный, крупный и доступен одним нажатием.
- Нельзя прятать Emergency Stop в меню.
- Все опасные действия требуют отдельного подтверждения.
- Для ручного движения использовать sliders, step buttons и jog buttons.
- Добавить dead-man control: если пользователь отпустил кнопку движения, движение прекращается.
- Добавить вибрацию телефона через Vibration API, если доступно.

Экраны:
1. Dashboard: camera, status, Mega, limit switches, homed/calibrated, ESTOP, HOME, AI mode, Manual mode.
2. Camera: stream, snapshot, FPS, AI/object detection overlay.
3. Manual Control: sliders, jog, gripper, speed limit, HOME, STOP.
4. Homing: home all, home axis, limit switch state, safety warning, homing result.
5. AI Command: text command, voice input, send, JSON preview, Confirm/Reject, AI explanation, forbidden rejection.
6. Recipes: recipe list, risk level, requirements, current step, pause, abort, preflight.
7. Calibration: axis, slow move, save min/max/home, invert, save config.
8. Settings: backend address, serial port, simulator/real mode, AI status, VPN status, camera, dark theme, auth token/PIN, export/import config.

PWA:
- Vite + React.
- CSS variables для dark theme.
- manifest: name "CookBot", short_name "CookBot", display standalone, dark colors.
- Service worker кэширует shell приложения.
- Не кэшировать camera stream и API-команды.
- Live state через WebSocket.
- Camera stream через MJPEG.
- При потере WebSocket блокировать новые команды движения.
- При потере связи с Mega блокировать управление рукой.
- При ESTOP блокировать все движения, кроме разрешённого CLEAR_ESTOP.

# Recipe Engine

Рецепты хранятся в YAML.
AI не должен напрямую генерировать движения для готовки.
AI может выбрать рецепт, заполнить параметры, объяснить план, попросить подтверждение, остановить выполнение, задать уточняющий вопрос.

Recipe Engine должен:
- загружать рецепт;
- проверять доступный режим;
- проверять, что gripper подходит;
- проверять homing/calibration;
- проверять концевики;
- выполнять preflight checklist;
- выполнять шаги последовательно;
- перед рискованным шагом запрашивать подтверждение;
- при ошибке останавливать выполнение;
- логировать каждый шаг.

Добавить безопасные рецепты:
- test_recipe.yaml
- stir_cold_ingredients.yaml
- move_safe_object.yaml

Добавить заблокированный пример:
- supervised_scrambled_eggs.locked_example.yaml
Причина блокировки: нет датчика температуры, нет heat-safe/food-safe подтверждённого инструмента, нет безопасного appliance interface.

# AI mode

Использовать OpenAI-compatible API.
Переменные окружения:
- AI_API_BASE_URL
- AI_API_KEY
- AI_MODEL

Не хардкодить ключи.
Не добавлять генераторы бесплатных ключей.
Не добавлять обходы, взломы, scraping или чужие ключи.
Если AI_API_KEY отсутствует, использовать mock_ai_client.

AI получает:
- команду пользователя;
- snapshot с камеры;
- состояние руки;
- состояние Mega;
- состояние концевиков;
- состояние homing/calibration;
- состояние камеры;
- текущий system state;
- доступные рецепты;
- текущий safety mode;
- ограничения.

AI возвращает только JSON:
{
  "intent": "cook_recipe|select_recipe|ask_user|refuse|manual_help|stop",
  "recipe_id": "string|null",
  "risk_level": "low|medium|high|forbidden",
  "confidence": 0.0,
  "requires_user_confirmation": true,
  "preflight_required": true,
  "missing_requirements": [],
  "steps_preview": [],
  "final_message": "string"
}

AI не может:
- отправлять команды напрямую на Mega;
- генерировать код для исполнения;
- включать нагрев;
- обходить ESTOP;
- отключать safety layer;
- выполнять рецепт, если preflight не пройден;
- работать с горячими объектами без подтверждения и датчиков;
- использовать ножи;
- работать с открытым огнём;
- работать без камеры в автономном режиме;
- считать позицию точной без homing/calibration;
- считать координаты объекта точными без camera/workspace calibration.

Если пользователь просит "приготовь яичницу":
- В assistant_mode отказать и объяснить, что нужен supervised/advanced mode.
- Если нет датчика температуры, отказать для автономного исполнения.
- Если нет heat-safe tool, отказать.
- Если нет food-safe tool, запретить контакт с едой.
- Если advanced_kitchen_lab_mode включён, показать locked recipe, missing requirements и запросить подготовку системы.
- Нельзя начинать готовку автоматически.

# Security

- API key хранить только в environment variables или .env.
- .env не коммитить.
- Добавить .gitignore.
- Web UI должен иметь auth token/PIN.
- По умолчанию backend слушает только локальную сеть.
- Не открывать управление роботом в интернет.
- Не отдавать camera stream без авторизации.
- Не логировать API key.
- Не логировать полные изображения без debug mode.
- Добавить rate limiting команд.
- Добавить command id/nonce.
- Добавить CORS config.
- Добавить предупреждение: не пробрасывать порт управления роботом наружу.

# VPN

- Добавить optional WireGuard split tunnel.
- VPN нужен только для AI API.
- Локальная связь телефона с UNO Q должна идти напрямую через Wi-Fi/LAN.
- Не делать full-tunnel по умолчанию.
- Локальные сети не отправлять через VPN:
  - 192.168.0.0/16
  - 10.0.0.0/8
  - 172.16.0.0/12
- Добавить route_check.py.

# Human Safety

В MVP:
- Сделать manual checkbox: "workspace is clear".
- Перед recipe/supervised cooking пользователь обязан подтвердить, что зона свободна.
- Если workspace_clear=false, движение запрещено.
- Robot motion near stove запрещён, если workspace_clear=false.
- Recipe start запрещён, если пользователь не подтвердил свободную зону.
- При любом сомнении система спрашивает пользователя.

# Logging

Добавить structured logs в JSONL.

Логировать:
- timestamp;
- source: ui/ai/backend/mega/recipe/safety;
- command_id;
- user_command;
- ai_response_id;
- validated_plan;
- rejected_reason;
- mega_command;
- mega_response;
- state_before;
- state_after;
- limit_switch_state;
- homing_result;
- errors;
- estop events;
- recipe step start/end.

Не логировать:
- AI_API_KEY;
- secret tokens;
- полные изображения, кроме debug mode.

# No-Hardware Development and Testing Loop

Разработка должна выполняться так, чтобы весь проект можно было тестировать без реального железа.

Codex должен:
- сначала реализовать simulator mode;
- затем реализовать fake_mega mode;
- затем писать backend, web app, AI layer и recipe engine так, чтобы они работали через simulator/fake_mega;
- не требовать подключённую Arduino Mega для запуска backend;
- не требовать реальную камеру для запуска UI;
- не требовать реальный AI API key для тестов;
- не требовать реальную роботизированную руку для прохождения тестов.

Если железо недоступно:
- использовать fake_mega;
- mock camera;
- mock AI client;
- mock limit switches;
- simulated workspace;
- sample snapshots;
- predefined recipes;
- simulator state.

Цикл разработки:
1. Создать минимальную структуру проекта.
2. Реализовать конфиги.
3. Реализовать fake_mega.
4. Реализовать simulator.
5. Реализовать protocol tests.
6. Реализовать backend.
7. Реализовать web app.
8. Реализовать camera mock.
9. Реализовать AI mock.
10. Реализовать safety tests.
11. Реализовать recipe tests.
12. Запустить все тесты.
13. Исправить ошибки.
14. Повторять тестирование и исправление, пока проект не будет проходить acceptance criteria.

Важно:
- Не останавливаться после генерации файлов.
- Не писать "требуется протестировать вручную" как замену автоматическим тестам.
- Не считать проект готовым, если тесты не запускаются.
- Не считать проект готовым, если backend падает без железа.
- Не считать проект готовым, если web app не собирается.
- Не считать проект готовым, если fake_mega не эмулирует базовые команды Mega.
- Не считать проект готовым, если команда ESTOP не очищает очередь команд.
- Не считать проект готовым, если forbidden AI command не отклоняется.
- Не считать проект готовым, если recipe engine можно обойти прямой AI-командой.

# check_all.sh / Makefile

Добавить Makefile или scripts/check_all.sh.

scripts/check_all.sh должен запускать:
Backend:
- python -m pytest tests/
- python -m compileall unoq_backend
- запуск backend в simulator mode и проверка /health
- проверка /state
- проверка /camera/snapshot с mock camera
- проверка /ai/command с mock AI
- проверка forbidden commands

Web app:
- npm install
- npm run build
- если есть тесты, npm test

Fake Mega:
- запуск fake_mega;
- отправка hello;
- отправка ping;
- отправка get_state;
- отправка home_all;
- отправка set_joint;
- отправка estop;
- проверка ошибок limit switch и not_homed.

Arduino Mega firmware:
- код должен быть написан так, чтобы компилировался в Arduino IDE или arduino-cli;
- если arduino-cli доступен, добавить команду compile;
- если arduino-cli недоступен, check_all.sh не должен падать полностью, а должен вывести предупреждение.

# Definition of Done для no-hardware версии

Проект считается завершённым на этапе no-hardware MVP, если:
- backend запускается без Arduino Mega;
- backend запускается без камеры;
- backend запускается без AI API key;
- web app собирается;
- телефонный UI имеет dark theme;
- simulator mode работает;
- fake_mega mode работает;
- mock camera работает;
- mock AI работает;
- ESTOP работает в simulator/fake_mega;
- homing имитируется;
- limit switches имитируются;
- forbidden cooking commands отклоняются;
- recipe без нагрева проходит preflight и может быть выполнен в симуляторе;
- locked recipe "supervised_scrambled_eggs" не запускается;
- все pytest тесты проходят;
- README содержит команду запуска no-hardware режима.

# Implementation Constraints

Не использовать ROS2 в MVP.
Не использовать Kubernetes, Docker Swarm, cloud backend или внешнюю базу данных в MVP.
Не требовать постоянный интернет для ручного управления.
Не требовать AI API для ручного управления.
Не требовать VPN для локального UI.
Не делать full autonomous cooking в MVP.
Не делать управление сетевым напряжением самодельным реле.
Не реализовывать смену насадок.
Не требовать энкодеры или абсолютные датчики положения.
Не притворяться, что концевики дают точное положение осей.
Не писать магическую автономию.
Не выполнять произвольный код, сгенерированный AI.
Не обходить safety layer.
Не открывать управление роботом в интернет.

# Acceptance Criteria

MVP-1 готов, если:
- backend запускается одной командой;
- web UI открывается с телефона;
- тёмная тема работает;
- camera stream работает или корректно показывает ошибку;
- simulator mode работает без Mega;
- fake_mega mode проходит тесты;
- Mega firmware компилируется или есть понятная инструкция компиляции;
- UNO Q может отправить hello/ping/get_state на Mega или fake_mega;
- ESTOP очищает очередь команд;
- forbidden AI command отклоняется;
- тесты safety/protocol/schema проходят.

MVP-2 готов, если:
- можно управлять всеми осями;
- gripper работает;
- концевики читаются;
- homing работает;
- calibration сохраняется;
- real motion невозможен без homing/calibration;
- углы вне лимитов отклоняются на UNO Q и Mega;
- сработавший концевик останавливает движение.

Recipe MVP готов, если:
- recipe загружается из YAML;
- preflight checklist работает;
- рецепт без нагрева выполняется пошагово;
- pause/abort/estop работают;
- AI не может обойти Recipe Engine;
- команда "приготовь яичницу" не запускает автономное приготовление без missing requirements.

# Что нужно выдать

1. Полную структуру проекта.
2. Все основные файлы с кодом.
3. README.md.
4. Makefile или scripts/check_all.sh.
5. docs/architecture.md.
6. docs/wiring.md.
7. docs/safety.md.
8. docs/homing_and_limits.md.
9. docs/calibration.md.
10. docs/ai_mode.md.
11. docs/robot_cook_architecture.md.
12. docs/kitchen_station.md.
13. docs/recipe_format.md.
14. docs/food_safety.md.
15. docs/vpn_split_tunnel.md.
16. docs/no_hardware_testing.md.
17. docs/reference_links.md со всеми ссылками на документацию.
18. docs/vendor_robot_notes.md:
    - какая информация о роботе подтверждена;
    - какая информация неизвестна;
    - какие параметры требуют ручной проверки;
    - какие значения временно заданы как safe defaults;
    - какие параметры нужно будет уточнить после доступа к реальному железу.
19. Python FastAPI backend.
20. Arduino Mega firmware.
21. React/Vite mobile PWA в тёмной теме.
22. Конфиги.
23. Тесты.
24. Simulator mode.
25. Fake Mega mode.
26. Mock camera.
27. Mock AI.
28. Инструкцию первого запуска.
29. Инструкцию homing.
30. Инструкцию calibration.
31. Инструкцию запуска без железа.
32. Инструкцию запуска с реальным Mega.
33. Итоговый отчёт:
    - какие файлы созданы;
    - как запустить no-hardware mode;
    - как запустить fake_mega;
    - как открыть web UI;
    - как запустить тесты;
    - какие тесты прошли;
    - какие проверки требуют реального железа позже;
    - какие функции пока являются mock/simulator.

# Final naming rule

Весь проект называется CookBot. Все папки, сервисы, README, UI-заголовки, PWA manifest, API title, тесты и документация должны использовать CookBot как основное имя проекта.

# Финальная инструкция

Начни с краткого плана реализации, затем создай файлы проекта. Если точные параметры руки неизвестны, не выдумывай их. Используй конфигурацию, homing, calibration wizard, концевики и безопасные значения-заглушки.

Работай итеративно. Не заканчивай ответ сразу после создания файлов. После реализации запусти доступные проверки, исправь ошибки и доведи no-hardware MVP до состояния, где он запускается, тестируется и проходит acceptance criteria. Реальное железо должно понадобиться только после того, как simulator/fake_mega версия уже работает.
