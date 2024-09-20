from microbit import button_a, i2c, sleep, pin14, pin15, pin8, pin12
from machine import time_pulse_us
from utime import ticks_us, ticks_diff
from lights_controller import LightsController

class Konstanty:
    NEDEFINOVANO = "nedefinovano"

    LEVY = "levy"
    PRAVY = "pravy"

    DOPREDU = "dopredu"
    DOZADU = "dozadu"

    ENKODER = "enkoder"
    PR_ENKODER = PRAVY + "_" + ENKODER
    LV_ENKODER = LEVY + "_" + ENKODER

    IR = "IR"
    PR_IR = PRAVY + "_" + IR
    LV_IR = LEVY + "_" + IR

    SENZOR_CARY = "senzor_cary"
    PR_S_CARY = PRAVY + "_" + SENZOR_CARY
    LV_S_CARY = LEVY + "_" + SENZOR_CARY
    PROS_S_CARY = "prostredni_" + SENZOR_CARY

    PI = 3.14159265359

class KalibracniFaktory:

    def __init__(self, min_rychlost, min_pwm_rozjezd, min_pwm_dojezd, a, b):
        self.min_rychlost = min_rychlost
        self.min_pwm_rozjezd = min_pwm_rozjezd
        self.min_pwm_dojezd = min_pwm_dojezd
        self.a = a
        self.b = b

class AdaptiveSpeedController:
    def __init__(self, desired_distance, max_speed, Kp, dead_zone):
        self.desired_distance = desired_distance
        self.max_speed = max_speed
        self.Kp = Kp
        self.dead_zone = dead_zone
        self.running = False

    def compute_speed(self, vzdalenost):
        if vzdalenost > 0:
            error = vzdalenost - self.desired_distance
            if abs(error) < self.dead_zone:
                speed = 0
            else:
                speed = self.Kp * error
                speed = max(min(speed, self.max_speed), -self.max_speed)
            return speed
        else:
            return 0

class Robot:

    def __init__(self, rozchod_kol, prumer_kola, kalibrace_levy, kalibrace_pravy, nova_verze=True):
        """
        Konstruktor tridy
        """
        self.__d = rozchod_kol/2
        self.__prumer_kola = prumer_kola

        self.__levy_motor = Motor(Konstanty.LEVY, self.__prumer_kola, kalibrace_levy, nova_verze)
        self.__pravy_motor = Motor(Konstanty.PRAVY, self.__prumer_kola, kalibrace_pravy, nova_verze)
        self.__inicializovano = False
        self.controller = None
        self.ultrasonic_sensor = None
        self.lights_controller = LightsController()
        self.lights_controller.turn_on_lights()

    def inicializuj(self):
        i2c.init(400000)
        self.__levy_motor.inicializuj()
        self.__pravy_motor.inicializuj()
        self.ultrasonic_sensor = Ultrazvuk()
        self.__inicializovano = True

    def zmer_vzdalenost(self):
        if self.ultrasonic_sensor:
            return self.ultrasonic_sensor.zmer_vzdalenost()
        else:
            return -1

    # pokrocily ukol 7
    def jed(self, dopredna_rychlost: float, uhlova_rychlost: float):
        """Pohybuj se zadanym  pohybem slozenym z dopredne rychlosti v a uhlove rychlosti"""

        if not self.__inicializovano:
            return -1
        # kinematika diferencionalniho podvozku - lekce 7
        dopr_rychlost_leve = dopredna_rychlost - self.__d * uhlova_rychlost
        dopr_rychlost_prave = dopredna_rychlost + self.__d * uhlova_rychlost

        # vyuziji funkce tridy motor
        self.__levy_motor.jed_doprednou_rychlosti(dopr_rychlost_leve)
        self.__pravy_motor.jed_doprednou_rychlosti(dopr_rychlost_prave)

        return 0

    def aktualizuj_se(self):
        self.__levy_motor.aktualizuj_se()
        self.__pravy_motor.aktualizuj_se()

    def set_tempomat(self, max_speed):
        self.__max = max_speed

    def set_adaptive_speed_controller(self, desired_distance, max_speed, Kp, dead_zone):
        self.controller = AdaptiveSpeedController(desired_distance, max_speed, Kp, dead_zone)

    def start_adaptive_speed_control(self):
        if self.controller:
            self.controller.running = True
            self.jed(0, 0)
            while self.controller.running and not button_a.was_pressed():
                vzdalenost = self.zmer_vzdalenost()
                print("Distance: {:.2f} m".format(vzdalenost))
                speed = self.controller.compute_speed(vzdalenost)
                self.jed(speed, 0)
                sleep(100)
                self.aktualizuj_se()
            self.jed(0, 0)
        else:
            print("Adaptive speed controller not set.")

    def stop_adaptive_speed_control(self):
        if self.controller:
            self.controller.running = False
            self.jed(0, 0)
        else:
            print("Adaptive speed controller not set.")

class Senzory:

    def __init__(self, nova_verze=True, debug=False):
        self.nova_verze = nova_verze
        self.DEBUG = debug

    def precti_senzory(self):
        surova_data_byte = i2c.read(0x38, 1)
        if self.DEBUG:
            print("surova data", surova_data_byte)
        bitove_pole = self.__byte_na_bity(surova_data_byte)

        senzoricka_data = {}

        if not self.nova_verze:
            senzoricka_data[Konstanty.LV_ENKODER] = bitove_pole[9]
            senzoricka_data[Konstanty.PR_ENKODER] = bitove_pole[8]

        senzoricka_data[Konstanty.LV_S_CARY] = bitove_pole[7]
        senzoricka_data[Konstanty.PROS_S_CARY] = bitove_pole[6]
        senzoricka_data[Konstanty.PR_S_CARY] = bitove_pole[5]
        senzoricka_data[Konstanty.LV_IR] = bitove_pole[4]
        senzoricka_data[Konstanty.PR_IR] = bitove_pole[3]

        return senzoricka_data

    def __byte_na_bity(self, data_bytes):

        data_int = int.from_bytes(data_bytes, "big")
        bit_pole_string = bin(data_int)

        if self.DEBUG:
            print("data_int", data_int)
            print("bit pole", bit_pole_string)

        return bit_pole_string

class Enkoder:

    def __init__(self, jmeno, perioda_rychlosti=1, nova_verze=True, debug=False):
        self.__jmeno = jmeno
        self.__perioda_rychlosti = perioda_rychlosti*1000000  # na us

        self.__nova_verze = nova_verze
        self.__tiky = 0
        self.__posledni_hodnota = -1
        self.__tiky_na_otocku = 40
        self.__DEBUG = debug
        self.__inicializovano = False
        self.__cas_posledni_rychlosti = ticks_us()
        self.__radiany_za_sekundu = 0

        if not self.__nova_verze:
            self.__senzory = Senzory(False, debug)

    def inicializuj(self):
        self.__posledni_hodnota = self.__aktualni_hodnota()
        self.__inicializovano = True

    def __aktualni_hodnota(self):
        if self.__nova_verze:
            if self.__jmeno == Konstanty.PR_ENKODER:
                return pin15.read_digital()
            elif self.__jmeno == Konstanty.LV_ENKODER:
                return pin14.read_digital()
            else:
                return -2
        else:
            senzoricka_data = self.__senzory.precti_senzory()

            if self.__jmeno == Konstanty.LV_ENKODER or self.__jmeno == Konstanty.PR_ENKODER:
                return int(senzoricka_data[self.__jmeno])
            else:
                return -2

    def aktualizuj_se(self):
        if self.__DEBUG:
            print("v aktualizuj", self.__tiky)
        if self.__posledni_hodnota == -1:
            if self.__DEBUG:
                print("posledni_hodnota neni nastavena", self.__posledni_hodnota)
            return -1

        aktualni_enkoder = self.__aktualni_hodnota()
        if self.__DEBUG:
            print("aktualni enkoder", aktualni_enkoder)

        if aktualni_enkoder >= 0:  # nenastaly zadne chyby
            if self.__posledni_hodnota != aktualni_enkoder:
                self.__posledni_hodnota = aktualni_enkoder
                self.__tiky += 1
        else:
            return aktualni_enkoder

        return 0

    def __us_na_s(self, cas):
        return cas/1000000

    def vypocti_rychlost(self):
        cas_ted = ticks_us()
        interval_us = ticks_diff(cas_ted, self.__cas_posledni_rychlosti)
        if interval_us >= self.__perioda_rychlosti:
            interval_s = self.__us_na_s(interval_us)
            otacky = self.__tiky/self.__tiky_na_otocku
            radiany = otacky * 2 * Konstanty.PI
            self.__radiany_za_sekundu = radiany / interval_s
            self.__tiky = 0
            self.__cas_posledni_rychlosti = cas_ted

        return self.__radiany_za_sekundu

class Motor:
    def __init__(self, jmeno, prumer_kola, kalibrace, nova_verze=True, debug=False):
        if jmeno == Konstanty.LEVY:
            self.__kanal_dopredu = b"\x05"
            self.__kanal_dozadu = b"\x04"
        elif jmeno == Konstanty.PRAVY:
            self.__kanal_dopredu = b"\x03"
            self.__kanal_dozadu = b"\x02"
        else:
            raise AttributeError("spatne jmeno motoru" + str(jmeno))

        self.__kalibrace = kalibrace

        self.__DEBUG = debug
        self.__jmeno = jmeno
        self.__prumer_kola = prumer_kola
        self.__enkoder = Enkoder(jmeno + "_enkoder", 1, nova_verze, debug)
        self.__smer = Konstanty.NEDEFINOVANO
        self.__inicializovano = False
        self.__rychlost_byla_zadana = False
        self.__min_pwm = 0
        self.__perioda_regulace = 1000000 #v microsekundach
        self.__cas_posledni_regulace = 0

    def inicializuj(self):
        # self.enkoder.inicializuj()
        # probud cip motoru
        i2c.write(0x70, b"\x00\x01")
        i2c.write(0x70, b"\xE8\xAA")

        self.__enkoder.inicializuj()
        self.__jed_PWM(0)

        self.__inicializovano = True

        self.__cas_posledni_regulace = ticks_us()

    def jed_doprednou_rychlosti(self, v: float):
        print("jed_dopred_rych:"+str(v))
        """
        Rozjede motor pozadovanou doprednou rychlosti
        """
        if not self.__inicializovano:
            print("Motor not initialized")
            return -1

        self.__pozadovana_uhlova_r_kola = self.__dopredna_na_uhlovou(v)
        print("pozadovana uhlova", self.__pozadovana_uhlova_r_kola)

        self.__rychlost_byla_zadana = True

        # pouziji funkce abs pro vypocteni absolutni hodnoty
        # PWM je vzdy pozitivni
        # znamenko uhlove rychlosti ovlivni smer
        prvni_PWM = self.__uhlova_na_PWM(abs(self.__pozadovana_uhlova_r_kola))
        print("prvni_PWM", prvni_PWM)

        if self.__pozadovana_uhlova_r_kola > 0:
            self.__smer = Konstanty.DOPREDU
        elif self.__pozadovana_uhlova_r_kola < 0:
            self.__smer = Konstanty.DOZADU
        else: # = 0
            self.__smer = Konstanty.NEDEFINOVANO

        return self.__jed_PWM(prvni_PWM)

    def __dopredna_na_uhlovou(self, v: float):
        """
        Prepocita doprednou rychlost kola na uhlovou
        """
        return v/(self.__prumer_kola/2)

    def __uhlova_na_PWM(self, uhlova):
        """
        Prepocte uhlovou rychlost na PWM s vyuzitim dat z kalibrace
        """
        if(uhlova == 0):
            return 0
        else:
            return int(self.__kalibrace.a*uhlova + self.__kalibrace.b)

    def __jed_PWM(self, PWM):
        je_vse_ok = -2
        if self.__smer == Konstanty.DOPREDU:
            je_vse_ok  = self.__nastav_PWM_kanaly(self.__kanal_dopredu, self.__kanal_dozadu, PWM)
        elif self.__smer == Konstanty.DOZADU:
            je_vse_ok  = self.__nastav_PWM_kanaly(self.__kanal_dozadu, self.__kanal_dopredu, PWM)
        elif self.__smer == Konstanty.NEDEFINOVANO:
            if PWM == 0:
                je_vse_ok = self.__nastav_PWM_kanaly(self.__kanal_dozadu, self.__kanal_dopredu, PWM)
            else:
                je_vse_ok = -1
        else:
            je_vse_ok = -3

        return je_vse_ok

    def __nastav_PWM_kanaly(self, kanal_on, kanal_off, PWM):
        # TODO zkontroluj, ze motor byl inicializovan
        i2c.write(0x70, kanal_off + bytes([0]))
        i2c.write(0x70, kanal_on + bytes([PWM]))
        self.__PWM = PWM
        return 0

    def aktualizuj_se(self):
        if not self.__inicializovano:
            return -1
        self.__enkoder.aktualizuj_se()
        cas_ted = ticks_us()
        cas_rozdil = ticks_diff(cas_ted, self.__cas_posledni_regulace)

        navratova_hodnota = 0
        if cas_rozdil > self.__perioda_regulace:
            navratova_hodnota = self.__reguluj_otacky()
            self.__cas_posledni_regulace = cas_ted

        return navratova_hodnota

    def __reguluj_otacky(self):

        if not self.__inicializovano:
            return -1

        if not self.__rychlost_byla_zadana:
            return -2

        P = 6

        aktualni_rychlost = self.__enkoder.vypocti_rychlost()
        # aktualni_rychlost bude vzdy pozitivni
        # musim tedy kombinovat se smerem, kterym se pohybuji
        if self.__pozadovana_uhlova_r_kola < 0:
            aktualni_rychlost *= -1

        error = self.__pozadovana_uhlova_r_kola - aktualni_rychlost
        akcni_zasah = P*error
        if self.__DEBUG:
            print((aktualni_rychlost,error, akcni_zasah))
        return self.__zmen_PWM_o(akcni_zasah)

    def __zmen_PWM_o(self, akcni_zasah):
        # error a tim padem i akcni_zasah muze byt jak pozitivni tak negativni, nezavisle na smeru
        akcni_zasah = int(akcni_zasah) #PWM je v celych cislech

        if self.__smer == Konstanty.DOZADU:
            # Pro j�zdu dozadu invertujeme akcni_zasah
            akcni_zasah *= -1

        nove_PWM = self.__PWM + akcni_zasah

        if nove_PWM > 255:
            nove_PWM = 255

        if nove_PWM < 0:
            nove_PWM  = 0
        if self.__DEBUG:
            print(nove_PWM)
        return self.__jed_PWM(nove_PWM)

class Ultrazvuk:

    def __init__(self):
        self.__trigger = pin8
        self.__echo = pin12

        self.__trigger.write_digital(0)
        self.__echo.read_digital()

    def zmer_vzdalenost(self):

        rychlost_zvuku = 340 # m/s

        self.__trigger.write_digital(1)
        self.__trigger.write_digital(0)

        zmereny_cas_us = time_pulse_us(self.__echo, 1)
        if zmereny_cas_us < 0:
            return zmereny_cas_us

        zmereny_cas_s = zmereny_cas_us/ 1000000
        vzdalenost = zmereny_cas_s*rychlost_zvuku/2

        return vzdalenost
        

def start_robot():
    print("startRobot")
    min_rychlost = 1.240075
    min_pwm_rozjezd = 61
    min_pwm_dojezd = 41
    a = 15.22801354
    b = 42.27615142

    levy_faktor = KalibracniFaktory(min_rychlost, min_pwm_rozjezd, min_pwm_dojezd, a, b)

    min_rychlost = 0.1553497
    min_pwm_rozjezd = 37
    min_pwm_dojezd = 37
    a = 17.05925837
    b = 27.05851914

    pravy_faktor = KalibracniFaktory(min_rychlost, min_pwm_rozjezd, min_pwm_dojezd, a, b)

    robot = Robot(0.15, 0.067, levy_faktor, pravy_faktor, True)
    robot.inicializuj()

    desired_distance = 0.2 
    max_speed = 0.3 
    Kp = 1
    dead_zone = 0.01

    robot.set_adaptive_speed_controller(desired_distance, max_speed, Kp, dead_zone)
    robot.start_adaptive_speed_control()

if __name__ == "__main__":
    print("start")
    start_robot()

