import threading
from pynput import keyboard

def background_task():
    try:
        # Simulate what pynput does internally that crashes
        k = keyboard.KeyCode.from_char('a')
        print("Success:", k)
    except Exception as e:
        print("Error:", e)

t = threading.Thread(target=background_task)
t.start()
t.join()
