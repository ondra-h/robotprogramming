from microbit import i2c
from microbit import sleep

def drive(speed, rotation):
    d = 0.08  

    v_l = int(speed - d * rotation)
    v_r = int(speed + d * rotation)

    v_l = max(-255, min(255, v_l))
    v_r = max(-255, min(255, v_r))

    # Control the left motor
    if v_l > 0:
        i2c.write(0x70, b'\x03' + bytes([v_l]))
        i2c.write(0x70, b'\x02' + bytes([0]))
    elif v_l < 0:
        i2c.write(0x70, b'\x02' + bytes([abs(v_l)]))
        i2c.write(0x70, b'\x03' + bytes([0]))
    else:
        i2c.write(0x70, b'\x03' + bytes([0]))
        i2c.write(0x70, b'\x02' + bytes([0]))

    # Control the right motor
    if v_r > 0:
        i2c.write(0x70, b'\x05' + bytes([v_r]))
        i2c.write(0x70, b'\x04' + bytes([0]))
    elif v_r < 0:
        i2c.write(0x70, b'\x04' + bytes([abs(v_r)]))
        i2c.write(0x70, b'\x05' + bytes([0]))
    else:
        i2c.write(0x70, b'\x05' + bytes([0]))
        i2c.write(0x70, b'\x04' + bytes([0]))

if __name__ == "__main__":
    i2c.init(freq=100000)
    i2c.write(0x70, b"\x00\x01")
    i2c.write(0x70, b"\xE8\xAA")
    sleep(100)

    drive(135, 0)
    sleep(1000)
    drive(0, 1350)
    sleep(1000)
    drive(0, 0)


