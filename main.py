from machine import Pin, PWM  # Pico의 GPIO와 PWM 기능을 불러옵니다.
import time  # 디바운싱과 부드러운 이동의 시간 측정을 불러옵니다.

BUTTON_PIN = 15  # 버튼을 Raspberry Pi Pico GP15에 연결합니다.
SERVO_PIN = 16  # 서보 신호를 Raspberry Pi Pico GP16에 연결합니다.
LED_PIN = 25  # Pico 내장 LED를 Raspberry Pi Pico GP25에 사용합니다.
START_ANGLE = 0  # 서보 시작 각도를 0도로 설정합니다.
END_ANGLE = 180  # 서보 목표 각도를 180도로 설정합니다.
DEBOUNCE_MS = 40  # 버튼 입력 안정화 시간을 40밀리초로 설정합니다.
STEP_INTERVAL_MS = 15  # 서보 각도 갱신 간격을 15밀리초로 설정합니다.
SERVO_FREQUENCY = 50  # 일반적인 아날로그 서보 주파수를 50Hz로 설정합니다.
SERVO_MIN_US = 500  # 0도에 대응하는 서보 펄스 폭을 500마이크로초로 설정합니다.
SERVO_MAX_US = 2500  # 180도에 대응하는 서보 펄스 폭을 2500마이크로초로 설정합니다.

button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)  # 버튼을 내부 풀업 입력으로 초기화합니다.
servo = PWM(Pin(SERVO_PIN))  # 서보 핀을 PWM 출력으로 초기화합니다.
led = PWM(Pin(LED_PIN))  # 내장 LED 핀을 PWM 출력으로 초기화합니다.
servo.freq(SERVO_FREQUENCY)  # 서보 PWM 주파수를 설정합니다.
led.freq(1000)  # LED PWM 주파수를 설정해 깜빡임을 줄입니다.
current_angle = START_ANGLE  # 현재 서보 각도를 0도로 초기화합니다.
moving = False  # 시작 시 서보가 이동 중이 아님을 기록합니다.
last_button_reading = 1  # 직전 버튼 원시 입력을 HIGH로 초기화합니다.
stable_button_state = 1  # 안정된 버튼 상태를 HIGH로 초기화합니다.
last_debounce_time = time.ticks_ms()  # 디바운스 기준 시각을 초기화합니다.
last_step_time = time.ticks_ms()  # 서보 이동 기준 시각을 초기화합니다.

def angle_to_brightness(angle):  # 각도를 0.0부터 1.0까지의 밝기로 변환합니다.
    return max(0.0, min(1.0, angle / END_ANGLE))  # 밝기를 안전한 범위로 제한해 반환합니다.

def write_servo(angle):  # 지정한 각도를 서보 PWM으로 출력합니다.
    pulse_us = SERVO_MIN_US + (SERVO_MAX_US - SERVO_MIN_US) * angle / END_ANGLE  # 각도에 맞는 펄스 폭을 계산합니다.
    duty = int(pulse_us * 65535 / (1000000 / SERVO_FREQUENCY))  # 펄스 폭을 MicroPython 듀티 범위로 변환합니다.
    servo.duty_u16(duty)  # 계산된 듀티를 서보에 출력합니다.

def write_led(angle):  # 지정한 각도에 비례하는 LED 밝기를 출력합니다.
    brightness = angle_to_brightness(angle)  # 0.0부터 1.0까지의 밝기 비율을 계산합니다.
    led.duty_u16(int(brightness * 65535))  # 밝기 비율을 16비트 PWM 듀티로 출력합니다.

def button_pressed_event():  # 디바운싱된 버튼 눌림 이벤트를 확인합니다.
    global last_button_reading, stable_button_state, last_debounce_time  # 버튼 상태 변수의 전역 수정을 허용합니다.
    reading = button.value()  # 버튼의 현재 원시 입력을 읽습니다.
    now = time.ticks_ms()  # 현재 시각을 밀리초로 읽습니다.
    if reading != last_button_reading:  # 원시 입력이 직전 입력과 달라졌는지 확인합니다.
        last_debounce_time = now  # 입력 변화 시각을 새로 기록합니다.
    last_button_reading = reading  # 다음 비교를 위해 원시 입력을 저장합니다.
    if time.ticks_diff(now, last_debounce_time) < DEBOUNCE_MS:  # 입력 안정화 시간이 지났는지 확인합니다.
        return False  # 아직 안정화되지 않았으므로 이벤트가 아님을 반환합니다.
    if reading != stable_button_state:  # 안정된 버튼 상태가 바뀌었는지 확인합니다.
        stable_button_state = reading  # 새로운 안정 상태를 저장합니다.
        return stable_button_state == 0  # 풀업 입력의 LOW 변화만 눌림 이벤트로 반환합니다.
    return False  # 새로운 눌림 이벤트가 없음을 반환합니다.

def start_motion():  # 서보의 0도에서 180도 이동을 시작합니다.
    global moving, last_step_time  # 이동 상태와 기준 시각의 전역 수정을 허용합니다.
    if not moving and current_angle == START_ANGLE:  # 이동 중이 아니고 시작 위치인지 확인합니다.
        moving = True  # 이동 상태를 활성화해 재입력을 막습니다.
        last_step_time = time.ticks_ms()  # 첫 이동의 기준 시각을 기록합니다.

def update_motion():  # 시간에 따라 서보와 LED를 함께 갱신합니다.
    global current_angle, moving, last_step_time  # 이동 상태 변수의 전역 수정을 허용합니다.
    if not moving:  # 현재 이동 중인지 확인합니다.
        return  # 이동 중이 아니면 현재 상태를 유지합니다.
    now = time.ticks_ms()  # 현재 시각을 읽습니다.
    if time.ticks_diff(now, last_step_time) < STEP_INTERVAL_MS:  # 다음 이동 시각이 되었는지 확인합니다.
        return  # 아직 간격이 지나지 않았으면 반환합니다.
    last_step_time = now  # 이번 이동 시각을 저장합니다.
    current_angle = min(END_ANGLE, current_angle + 1)  # 각도를 1도씩 증가시키고 목표를 넘지 않게 합니다.
    write_servo(current_angle)  # 증가한 각도를 서보에 출력합니다.
    write_led(current_angle)  # 증가한 각도에 비례한 밝기를 LED에 출력합니다.
    if current_angle >= END_ANGLE:  # 목표 각도에 도달했는지 확인합니다.
        moving = False  # 이동을 끝내 버튼 재입력을 안전하게 처리할 수 있게 합니다.

write_servo(START_ANGLE)  # 실행 직후 서보를 0도로 설정합니다.
write_led(START_ANGLE)  # 실행 직후 LED를 완전히 끕니다.

while True:  # Pico에서 제어 로직을 계속 반복합니다.
    if not moving and button_pressed_event():  # 이동 중이 아니면서 디바운싱된 눌림인지 확인합니다.
        start_motion()  # 버튼 이벤트에 따라 이동을 시작합니다.
    update_motion()  # 서보와 LED의 진행 상태를 갱신합니다.
    time.sleep_ms(1)  # CPU 점유를 낮추면서 입력 응답성을 유지합니다.
