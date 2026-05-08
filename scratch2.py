from pynput import keyboard

def on_press(key):
    pass
def on_release(key):
    pass

l = keyboard.Listener(on_press=on_press, on_release=on_release)
l.start()
l.join()
