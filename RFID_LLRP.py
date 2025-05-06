#!/usr/bin/env python

import time
import logging
import threading
from queue import Queue
from typing import Optional

from sllurp.llrp import (
    LLRP_DEFAULT_PORT,
    LLRPReaderClient,
    LLRPReaderConfig,
    LLRPReaderState,
)

# -------- RFID CONFIGURATION -------- #
PORT = LLRP_DEFAULT_PORT

# -------- GLOBALS -------- #
READER: Optional[LLRPReaderClient] = None
TAG_QUEUE = Queue()
TAG_DATA = []

# -------- LOGGING SETUP -------- #
logging.basicConfig(level=logging.INFO)
sllurp_logger = logging.getLogger("sllurp")
sllurp_logger.setLevel(logging.INFO)
sllurp_logger.addHandler(logging.StreamHandler())


# -------- CALLBACKS -------- #
def tag_report_cb(_reader, tag_reports):
    """Callback for tag reads"""
    global TAG_DATA
    TAG_DATA = [
        {
            "epc": tag["EPC"].decode("ascii"),
            "channel": tag["ChannelIndex"],
            "last_seen": tag["LastSeenTimestampUTC"],
            "seen_count": tag["TagSeenCount"],
        }
        for tag in tag_reports
    ]
    TAG_QUEUE.put(TAG_DATA)
    logging.info(f"📥 Received {len(tag_reports)} tag(s)")


def handle_event(_reader, event):
    """Callback for GPI or connection events"""
    if "GPIEvent" in event:
        gpi_event = event.get("GPIEvent")
        logging.info(f"🔌 GPI Event: {gpi_event}")

        if gpi_event and gpi_event.get("GPIPortNumber") == 1:
            if gpi_event.get("GPIEvent"):
                if READER and READER.is_alive():
                    logging.info("🟢 GPI: Starting inventory")
                    start_reading()
            else:
                logging.info("🛑 GPI: Stopping inventory")
                stop_reading()

    if "ConnectionAttemptEvent" in event:
        logging.info(f"🔄 Connection Event: {event['ConnectionAttemptEvent']}")
    else:
        logging.info(f"ℹ️ Other Event: {event}")


# -------- COMMAND FUNCTIONS -------- #
def clear_tag_data():
    global TAG_DATA
    TAG_DATA = []
    print("🧹 Tag data cleared.")


def start_reading():
    if READER and READER.is_alive():
        clear_tag_data()
        READER.llrp.startInventory()
        print("📡 Started inventory.")


def stop_reading():
    if READER and READER.is_alive():
        READER.llrp.stopPolitely()
        print("🛑 Stopped inventory.")


def print_reader_state():
    if READER and READER.is_alive():
        print(f"📊 Reader state: {LLRPReaderState.getStateName(READER.llrp.state)}")
    else:
        print("🔌 Reader not connected.")


# -------- THREAD: TAG DISPLAY -------- #
def process_tags_console():
    while True:
        if not TAG_QUEUE.empty():
            tags = TAG_QUEUE.get()
            print(f"\n📦 Tags read ({len(tags)}):")
            for tag in tags:
                print(f" - EPC: {tag['epc']} | Ch: {tag['channel']} | Seen: {tag['seen_count']}x")
        time.sleep(0.1)


# -------- USER INTERFACE LOOP -------- #
def user_interface():
    while True:
        print("\nCommands: [start] [stop] [clear] [state] [exit]")
        cmd = input(">> ").strip().lower()
        if cmd == "start":
            start_reading()
        elif cmd == "stop":
            stop_reading()
        elif cmd == "clear":
            clear_tag_data()
        elif cmd == "state":
            print_reader_state()
        elif cmd == "exit":
            stop_reading()
            break
        else:
            print("❓ Unknown command.")


# -------- MAIN -------- #

def main():
    global READER

    reader_ip = input("🔧 Enter RFID reader IP address (e.g., 192.168.1.100): ").strip()
    if not reader_ip:
        print("❌ No IP address entered. Exiting...")
        return

    print("🚀 Initializing RFID Reader...")
    config = LLRPReaderConfig()
    config.reset_on_connect = True
    config.start_inventory = False
    config.event_selector = {"GPIEvent": True}

    READER = LLRPReaderClient(reader_ip, PORT, config)
    READER.add_tag_report_callback(tag_report_cb)
    READER.add_event_callback(handle_event)
    READER.connect()

    print("✅ Reader connected. Ready for commands.")

    tag_thread = threading.Thread(target=process_tags_console, daemon=True)
    tag_thread.start()

    user_interface()

    if READER and READER.is_alive():
        READER.llrp.stopPolitely()
        READER.disconnect()
        print("👋 Reader disconnected. Exiting...")


if __name__ == "__main__":
    main()
