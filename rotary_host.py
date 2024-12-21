import tkinter as tk
import RPi.GPIO as GPIO
import argparse
import socket
import threading
import time

# GPIO pin configuration
CLK = 17  # Clock pin
DT = 18   # Data pin
BTN = 23  # Button pin

# Initialize the GPIO pins
GPIO.setmode(GPIO.BCM)
GPIO.setup(CLK, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(DT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BTN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Initialize rotary encoder value and button state
rotary_value = 0
button_state = 0  # 0: OFF, 1: ON

# Store last state of the CLK pin and button state
last_clk_state = GPIO.input(CLK)
last_button_pressed = False  # Tracks the last physical button press state

# Polling interval for rotary encoder in seconds
rotary_polling_interval = 0.001  # 1ms

# Update rotary logic
lock = threading.Lock()
def update_rotary_logic():
    """Update rotary value based on CLK and DT pin states with limits."""
    global rotary_value, last_clk_state

    current_clk_state = GPIO.input(CLK)
    if current_clk_state != last_clk_state:
        dt_state = GPIO.input(DT)
        if dt_state != current_clk_state:
            if rotary_value < 100:
                rotary_value += 1
        else:
            if rotary_value > 0:
                rotary_value -= 1

        print(f"[DEBUG] Rotary value updated to: {rotary_value}")

    last_clk_state = current_clk_state

# Update button state
def update_button_state():
    global button_state, last_button_pressed
    current_button_pressed = not GPIO.input(BTN)  # Button is active low
    if current_button_pressed and not last_button_pressed:
        # Toggle the button state on press
        button_state = 1 - button_state  # Toggle between 0 and 1
        print(f"[DEBUG] Button state toggled to: {'ON' if button_state else 'OFF'}")
    last_button_pressed = current_button_pressed

# Setup the server to listen for incoming clients
def setup_tcp_server(host, port, updates_per_second, headless=False):
    global rotary_value, button_state
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((host, port))
    server_socket.listen(1)  # Only one client is allowed at a time
    print(f"[INFO] TCP server listening on {host}:{port}")

    client_socket = None
    client_address = None

    def server_gui():
        if headless:
            return

        # Create the GUI application
        gui_root = tk.Tk()
        gui_root.title("Rotary Encoder Server GUI")

        # Create a label to display the rotary value and button state
        gui_label_var = tk.StringVar()
        gui_label_var.set(f"Rotary Value: {rotary_value};{'1' if button_state else '0'}")
        gui_label = tk.Label(gui_root, textvariable=gui_label_var, font=("Helvetica", 24))
        gui_label.pack(pady=20)

        def update_gui():
            gui_label_var.set(f"Rotary Value: {rotary_value};{'1' if button_state else '0'}")
            gui_root.after(10, update_gui)

        update_gui()
        try:
            gui_root.mainloop()
        except KeyboardInterrupt:
            print("[INFO] GUI interrupted.")

    if not headless:
        gui_thread = threading.Thread(target=server_gui, daemon=True)
        gui_thread.start()

    def rotary_update_and_send():
        nonlocal client_socket, client_address
        while True:
            update_rotary_logic()
            update_button_state()
            if client_socket:
                try:
                    message = f"{rotary_value};{button_state}".encode('utf-8')
                    client_socket.send(message)
                except Exception as e:
                    print(f"[ERROR] Lost connection to {client_address}: {e}")
                    client_socket.close()
                    client_socket, client_address = None, None
            time.sleep(1 / updates_per_second)

    rotary_thread = threading.Thread(target=rotary_update_and_send, daemon=True)
    rotary_thread.start()

    def rotary_polling_loop():
        while True:
            update_rotary_logic()
            update_button_state()
            time.sleep(rotary_polling_interval)

    rotary_polling_thread = threading.Thread(target=rotary_polling_loop, daemon=True)
    rotary_polling_thread.start()

    try:
        while True:
            print("[INFO] Waiting for a client to connect...")
            client_socket, client_address = server_socket.accept()
            print(f"[INFO] Client connected: {client_address}")
    except KeyboardInterrupt:
        print("[INFO] Server shutting down...")
    finally:
        server_socket.close()
        if client_socket:
            client_socket.close()

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Rotary Encoder GUI with TCP Server")
parser.add_argument("--server", "-s", type=int, help="Run in server mode and send updates via TCP. Provide updates per second.")
parser.add_argument("--host", type=str, default="0.0.0.0", help="Host IP address to bind the server (default: 0.0.0.0).")
parser.add_argument("--port", type=int, default=56969, help="Port to bind the server (default: 56969).")
parser.add_argument("--headless", "-L", action="store_true", help="Run in headless server mode without GUI.")
args = parser.parse_args()

if args.server:
    print("Starting TCP server...")
    setup_tcp_server(args.host, args.port, args.server, headless=args.headless)
else:
    # Create the GUI application
    root = tk.Tk()
    root.title("Rotary Encoder GUI")

    # Create a label to display the rotary value and button state
    label_var = tk.StringVar()
    label_var.set(f"Rotary Value: {rotary_value};{'1' if button_state else '0'}")
    label = tk.Label(root, textvariable=label_var, font=("Helvetica", 24))
    label.pack(pady=20)

    def update_gui():
        update_rotary_logic()
        update_button_state()
        label_var.set(f"Rotary Value: {rotary_value};{'1' if button_state else '0'}")
        root.after(10, update_gui)

    update_gui()

    try:
        # Run the GUI event loop
        root.mainloop()
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        GPIO.cleanup()
