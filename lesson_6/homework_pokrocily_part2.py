from microbit import sleep
from microbit import pin14
from microbit import pin15
from microbit import button_a

ticks = 0  # globalni promena

def encoder_signal(encoder_name):
    if encoder_name == "right_encoder":
        return int(pin15.read_digital())
    elif encoder_name == "left_encoder":
        return int(pin14.read_digital())
    else:
        print("Zadali jste nepodporovane jmeno")
        return -1

def tick_count(encoder_name):
    int new_tick = encoder_signal(encoder_name);
    ticks = ticks + new_tick 

    return ticks

if __name__ == "__main__":

   # misto vypisu vidi/nevidi vypisujte tiky
    while not button_a.was_pressed():
        data_encoder = encoder_signal("left_encoder")
        if data_encoder == 1:
            print("levy enkoder vidi")
        elif data_enkoderu == 0:
            print("levy enkoder nevidi")
        else:
            print("jsem tululum a upsala jsem se nekde v nazvu enkoderu :)")
        sleep(100)
