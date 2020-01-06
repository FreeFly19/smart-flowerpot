import os
import time
import ESP8266WebServer
import network
import machine

adc = machine.ADC(0)


def connect_to_wifi():
    if 'wifi.txt' not in os.listdir('.'):
        print('There is no wifi.txt file yet.')
        return False

    f = open('wifi.txt', 'r')
    f.seek(0)
    ssid = f.readline()[:-1]
    password = f.readline()[:-1]
    f.close()

    if ssid == "" or ssid is None:
        print('There is no ssid specified!')
        return False

    sta_if = network.WLAN(network.STA_IF)

    if not sta_if.active():
        sta_if.active(True)

    if sta_if.isconnected():
        if sta_if.config('essid') == ssid:
            print('Already connected to the WiFi point ' + ssid)
            return True
        else:
            print('Disconnecting from ' + sta_if.config('essid') + ' WiFi point...')
            sta_if.disconnect()

    sta_if.connect(ssid, password)
    print('Connecting to WiFi point "' + ssid + '", with password "' + password + '" ...')

    for i in range(20):
        if sta_if.isconnected():
            print('Connected!')
            return True
        print('.', end='')
        time.sleep(1)

    print("Connect attempt timed out\n")
    return False


is_real_time_received = False


def receive_and_set_real_time():
    global is_real_time_received
    from ntptime import settime
    settime()
    is_real_time_received = True

if connect_to_wifi():
    receive_and_set_real_time()

ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid='SmartFlowerpot', authmode=network.AUTH_WPA_WPA2_PSK, password="new-year-2020")


engine_pin = machine.Pin(2, machine.Pin.OUT)
engine_pin.off()

ESP8266WebServer.begin(80)

print("Server started @ ", ap.ifconfig()[0])


def handle_index(socket, args):
    socket.write("HTTP/1.1 200 OK\r\n")
    socket.write("Content-Type: text/html\r\n")
    socket.write("Content-Length: " + str(os.stat('index.html')[6]) + "\r\n")
    socket.write("\r\n")
    f = open('index.html', "rb")
    while True:
        data = f.read(64)
        if data == b"":
            break
        socket.write(data)
    f.close()


ESP8266WebServer.onPath("/", handle_index)


def handle_wifi_credentials(socket, args):
    f = open('wifi.txt', 'w+')
    f.write(args['SSID'])
    f.write('\n')
    f.write(args['password'])
    f.write('\n')
    f.close()
    if connect_to_wifi():
        response = 'Connected!<br><a href="/">Home</a>'
        try:
            receive_and_set_real_time()
        except:
            pass
    else:
        response = 'Connection Error<br><a href="/">Home</a>'

    socket.write("HTTP/1.1 200 OK\r\n")
    socket.write("Content-Type: text/html\r\n")
    socket.write("Content-Length: " + str(len(response)) + "\r\n")
    socket.write("\r\n")
    socket.write(response)


ESP8266WebServer.onPath("/api/wifi-connect", handle_wifi_credentials)


def handle_state(socket, args):
    sta_if = network.WLAN(network.STA_IF)
    response = '{"last_measurement_time":' + str(last_time_measured + 946684800) + \
               ', "last_measurement_value": ' + str(last_measured_value) + \
               ', "pour_measurement_min": ' + str(pour_measurement_range[0]) + \
               ', "pour_measurement_max": ' + str(pour_measurement_range[1]) + \
               ', "pour_hours_min": ' + str(pour_hours_range[0]) + \
               ', "pour_hours_max": ' + str(pour_hours_range[1]) + \
               ', "wifi_connection_ssid": "' + sta_if.config('essid') + '"'\
               ', "wifi_is_connected": ' + ('true' if sta_if.isconnected() else 'false') + \
               ', "current_time": ' + str(time.time() + 946684800) + '}'
    socket.write('HTTP/1.1 200 OK\r\n')
    socket.write('Content-Type: application/json\r\n')
    socket.write('Content-Length: ' + str(len(response)) + '\r\n')
    socket.write('\r\n')
    socket.write(response)


ESP8266WebServer.onPath("/api/state", handle_state)


def handle_pour_config(socket, args):
    change_pour_measurement_range(args['pour-measurement-min'], args['pour-measurement-max'])
    change_pour_hours_range(args['pour-hours-min'], args['pour-hours-max'])
    response = '{"message": "OK"}'
    socket.write('HTTP/1.1 200 OK\r\n')
    socket.write('Content-Type: application/json\r\n')
    socket.write('Content-Length: ' + str(len(response)) + '\r\n')
    socket.write('\r\n')
    socket.write(response)


ESP8266WebServer.onPath("/api/pour-properties", handle_pour_config)


def change_pour_measurement_range(min_val, max_val):
    f = open('pour_measurement_range.txt', 'w+')
    f.write(min_val)
    f.write('\n')
    f.write(max_val)
    f.write('\n')
    f.close()
    pour_measurement_range[0] = int(min_val)
    pour_measurement_range[1] = int(max_val)


def change_pour_hours_range(min_val, max_val):
    f = open('pour_hours_range.txt', 'w+')
    f.write(min_val)
    f.write('\n')
    f.write(max_val)
    f.write('\n')
    f.close()
    pour_hours_range[0] = int(min_val)
    pour_hours_range[1] = int(max_val)


pouring_duration = 5   # Seconds TODO: make it adjustable from frontend
measure_interval = 60  # Seconds TODO: make it adjustable from frontend

last_time_measured = time.time()
last_measured_value = adc.read()
pour_measurement_range = [650, 1022]
pour_hours_range = [13, 20]


if 'pour_measurement_range.txt' in os.listdir('.'):
    f = open('pour_measurement_range.txt', 'r')
    f.seek(0)
    pour_measurement_range[0] = int(f.readline()[:-1]) or pour_measurement_range[0]
    pour_measurement_range[1] = int(f.readline()[:-1]) or pour_measurement_range[1]
    f.close()

if 'pour_hours_range.txt' in os.listdir('.'):
    f = open('pour_hours_range.txt', 'r')
    f.seek(0)
    pour_hours_range[0] = int(f.readline()[:-1]) or pour_hours_range[0]
    pour_hours_range[1] = int(f.readline()[:-1]) or pour_hours_range[1]
    f.close()


try:
    while True:
        ESP8266WebServer.handleClient()
        if time.time() - last_time_measured > measure_interval:
            last_time_measured = time.time()
            last_measured_value = adc.read()

            if pour_measurement_range[0] <= last_measured_value <= pour_measurement_range[1]:
                print("Measured humidity value is suitable for pouring...")
                if is_real_time_received:
                    print("There is real time, comparing hours...")
                    if pour_hours_range[0] <= time.localtime()[3] <= pour_hours_range[1]:
                        print("Hours are suitable for pouring, activating engine...")
                        engine_pin.on()
                        time.sleep(pouring_duration)
                        engine_pin.off()
                        print("Poured!")
                    else:
                        print("Hours are not suitable for pouring, engine will be not activated.")
                else:
                    print("There is not real time receive, engine will be not activated.")
            else:
                print("Measured humidity value is fine, no need for pouring!")

except Exception as e:
    print(e)
    ESP8266WebServer.close()
