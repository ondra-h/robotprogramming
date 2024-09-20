from microbit import button_a, sleep, i2c, pin8, pin12, time_pulse_us
from cely_projekt import Konstanty, KalibracniFaktory, Robot

class Ultrazvuk:

    def __init__(self):
        self.__trigger = pin8
        self.__echo = pin12

        self.__trigger.write_digital(0)
        self.__echo.read_digital()

    def zmer_vzdalenost(self):

        rychlost_zvuku = 340  # m/s

        self.__trigger.write_digital(1)
        self.__trigger.write_digital(0)

        zmereny_cas_us = time_pulse_us(self.__echo, 1)
        if zmereny_cas_us < 0:
            return -1  # Return -1 if measurement failed

        zmereny_cas_s = zmereny_cas_us / 1000000
        vzdalenost = zmereny_cas_s * rychlost_zvuku / 2

        return vzdalenost

def start_robot(ult):

    min_rychlost = 0.31
    min_pwm_rozjezd = 47  # kalibrace vytiskne na konci pri "zrychluj"
    min_pwm_dojezd = 35   # kalibrace vytiskne na konci pri "zpomaluj"
    a = 15.22801354       # ziskej z excelu
    b = 42.27615142       # ziskej z excelu

    levy_faktor = KalibracniFaktory(min_rychlost, min_pwm_rozjezd, min_pwm_dojezd, a, b)

    min_rychlost = 0.7
    min_pwm_rozjezd = 39
    min_pwm_dojezd = 28
    a = 17.05925837
    b = 27.05851914

    pravy_faktor = KalibracniFaktory(min_rychlost, min_pwm_rozjezd, min_pwm_dojezd, a, b)

    robot = Robot(0.15, 0.067, levy_faktor, pravy_faktor, True)
    robot.inicializuj()
    robot.jed(0.067 * Konstanty.PI, 0)  # Start moving forward

    while not button_a.was_pressed():
        vzdalenost = ult.zmer_vzdalenost()
        if vzdalenost > 0 and vzdalenost <= 0.3:
            robot.jed(0, 0)  # Stop the robot
            break
        sleep(5)
        robot.aktualizuj_se()

    robot.jed(0, 0)  # Ensure the robot is stopped when exiting the loop

if __name__ == "__main__":
    ult = Ultrazvuk()
    start_robot(ult)

