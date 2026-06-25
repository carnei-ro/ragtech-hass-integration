#!/usr/bin/env python3
import serial
import time
import json

SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 2560
TIMEOUT = 5
# DATA_FILE = "./ragtech-ups.data"

REQUEST_COMMAND = bytes.fromhex("AA0400801E9E")
#VALORES NOMINAIS
def parse_data(data):
    hex_str = ''.join(f'{byte:02x}' for byte in data)

    if hex_str.startswith("aa21") and len(hex_str) >= 62:
        battery_charge = round(int(hex_str[16:18], 16) * 0.393)
        input_voltage = round(int(hex_str[52:54], 16) * 1.06)
        output_voltage = round(int(hex_str[60:62], 16) * 0.555)
        temperature = int(hex_str[30:32], 16)
        load = int(hex_str[28:30], 16)
        battery_voltage = round(int(hex_str[22:24], 16) * 0.1342, 2)
        frequency = round(int(hex_str[48:50], 16) * -0.1152 + 65, 2)
        current_out = round(int(hex_str[26:28], 16) * 0.120, 2)
        battery_status = 'FULL'

        apparent_power = round(output_voltage * current_out, 1)
        #Fator Potencia, de 0.7, neste caso 1.3 será o calculo
        power_factor = 1.3
        real_power = round(apparent_power * power_factor, 1)
        #Eficiencia = Fator da Eficiencia, os calculos com o multimetrio e também baseado no output do app da ragtech oficial
        efficiency = 0.60
        current_in = 0.0
        if input_voltage > 0:
            current_in = round((output_voltage * current_out) / (input_voltage * efficiency), 2)
        # Enhanced status logic
        if input_voltage < 100:
            if battery_charge < 30:
                ups_status = "LB"  # Low Battery
            else:
                ups_status = "OB"  # On Battery
        else:
            ups_status = "OL"  # On Line

        # Battery replacement detection (example logic)
        if battery_charge < 5:
            ups_status = "RB"

        # Charging/Discharging logic
        if input_voltage > output_voltage:
            ups_status += " CHRG"
            battery_status = "CHARGING"
        elif input_voltage != 0 and abs(input_voltage - output_voltage) / input_voltage > 0.10:
            ups_status += " DISCHRG"
            battery_status = "DISCHARGING"
        # Write updated data to NUT data file
        metrics = {
            "battery.charge": battery_charge,
            "battery.voltage": battery_voltage / 2,
            "battery.status": battery_status,
            "input.voltage": input_voltage,
            "input.current": current_in,
            "input.frequency": frequency,
            "output.voltage": output_voltage,
            "output.current": current_out,
            "output.power": apparent_power,
            "output.apower": real_power,
            "ups.temperature": temperature,
            "ups.load": load,
            "ups.status": ups_status,
        }
        return metrics
        # with open(DATA_FILE, 'w') as f:
        #     for k, v in metrics.items():
        #         f.write(f"{k}: {v}\n")

def main():
    try:
        with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT) as ser:
            ser.write(REQUEST_COMMAND)
            time.sleep(2)
            response = ser.read(64)
            print(json.dumps(parse_data(response)))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
