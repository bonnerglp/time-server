#!/usr/bin/env python3
import os
import pty
import fcntl
import termios
import tty
import select
import signal
import sys
import errno
import serial

RUN = True

def stop_handler(signum, frame):
    global RUN
    RUN = False

signal.signal(signal.SIGINT, stop_handler)
signal.signal(signal.SIGTERM, stop_handler)

def make_pty(link_path):
    master_fd, slave_fd = pty.openpty()
    slave_name = os.ttyname(slave_fd)

    # raw mode on slave
    attrs = termios.tcgetattr(slave_fd)
    tty.setraw(slave_fd)
    termios.tcsetattr(slave_fd, termios.TCSANOW, attrs)

    try:
        os.unlink(link_path)
    except FileNotFoundError:
        pass
    os.symlink(slave_name, link_path)
    return master_fd, slave_fd, slave_name

def set_nonblocking(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

def main():
    src = "/dev/ttyACM0"
    gpsd_link = "/tmp/zed_gpsd"
    ucenter_link = "/tmp/zed_ucenter"

    gpsd_master, gpsd_slave, gpsd_name = make_pty(gpsd_link)
    ucenter_master, ucenter_slave, ucenter_name = make_pty(ucenter_link)

    set_nonblocking(gpsd_master)
    set_nonblocking(ucenter_master)

    ser = serial.Serial(
        src,
        baudrate=115200,
        timeout=0,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
    )

    print(f"Reading {src}")
    print(f"gpsd PTY: {gpsd_name} -> {gpsd_link}")
    print(f"u-center PTY: {ucenter_name} -> {ucenter_link}")
    sys.stdout.flush()

    while RUN:
        rlist, _, _ = select.select([ser.fileno(), gpsd_master, ucenter_master], [], [], 0.2)

        for fd in rlist:
            if fd == ser.fileno():
                try:
                    data = ser.read(4096)
                except serial.SerialException:
                    data = b""
                if data:
                    for out_fd in (gpsd_master, ucenter_master):
                        try:
                            os.write(out_fd, data)
                        except OSError:
                            pass
            elif fd == gpsd_master:
                try:
                    data = os.read(gpsd_master, 1024)
                    if data:
                        ser.write(data)
                except OSError as e:
                    if e.errno not in (errno.EAGAIN, errno.EWOULDBLOCK):
                        pass
            elif fd == ucenter_master:
                try:
                    data = os.read(ucenter_master, 1024)
                    if data:
                        ser.write(data)
                except OSError as e:
                    if e.errno not in (errno.EAGAIN, errno.EWOULDBLOCK):
                        pass

    ser.close()

if __name__ == "__main__":
    main()
