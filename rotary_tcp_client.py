import argparse
import socket
import time
import os

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Rotary Encoder TCP Client")
parser.add_argument("host", type=str, help="IP address of the host running the TCP server.")
parser.add_argument("--port", type=int, default=56969, help="Port number of the TCP server (default: 56969).")
parser.add_argument("--output", type=str, default="rotary_values.txt", help="Output file to write the rotary values.")
parser.add_argument("--purge-interval", type=int, default=3600, help="Time in seconds to purge the output file (default: 3600 seconds / 1 hour).")
args = parser.parse_args()

# Setup TCP client
server_address = (args.host, args.port)

try:
    print(f"Attempting to connect to server at {args.host}:{args.port}...")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp_socket:
        tcp_socket.connect(server_address)
        print(f"Connected to server at {args.host}:{args.port}.")

        # Open the output file for writing
        try:
            output_file = open(args.output, "w")
            print(f"Writing rotary values to {args.output}...")

            start_time = time.time()
            last_value = None

            while True:
                try:
                    # Receive data from the server
                    data = tcp_socket.recv(1024)  # Buffer size is 1024 bytes
                    if not data:
                        print("[INFO] Server closed the connection.")
                        break

                    rotary_data = data.decode('utf-8')

                    # Only output if the value has changed
                    if rotary_data != last_value:
                        output_file.write(f"{rotary_data}\n")
                        output_file.flush()  # Ensure the data is written immediately
                        print(f"[DEBUG] Received rotary value: {rotary_data}")
                        last_value = rotary_data

                    # Check if purge interval has elapsed
                    current_time = time.time()
                    if current_time - start_time >= args.purge_interval:
                        print(f"[INFO] Purging output file {args.output} after {args.purge_interval} seconds.")
                        try:
                            output_file.close()
                            output_file = open(args.output, "w")  # Reopen and truncate the file
                        except Exception as purge_error:
                            print(f"[ERROR] Failed to purge file: {purge_error}")
                        start_time = current_time

                except Exception as e:
                    print(f"[ERROR] An unexpected error occurred: {e}")
                    break

        finally:
            if 'output_file' in locals() and not output_file.closed:
                output_file.close()

except KeyboardInterrupt:
    print("Exiting client...")
except Exception as e:
    print(f"[ERROR] Could not connect to the server: {e}")
