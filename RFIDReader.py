#!/usr/bin/env python

import time
import logging
import threading
from queue import Queue, Empty
from typing import Optional
from collections import deque

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
SEEN_TAGS = deque(maxlen=100)  # Keep latest 100 for reference

# -------- LOGGING SETUP -------- #
logging.basicConfig(level=logging.INFO)
sllurp_logger = logging.getLogger("sllurp")
sllurp_logger.setLevel(logging.INFO)
sllurp_logger.addHandler(logging.StreamHandler())


# -------- CALLBACKS -------- #
def tag_report_cb(_reader, tag_reports):
    """Callback for tag reads"""
    for tag in tag_reports:
        try:
            tag_data = {
                "epc": tag["EPC"].decode("ascii"),
                "channel": tag.get("ChannelIndex"),
                "last_seen": tag.get("LastSeenTimestampUTC"),
                "seen_count": tag.get("TagSeenCount"),
            }
            TAG_QUEUE.put(tag_data)
        except Exception as e:
            print(f"⚠️ Error parsing tag: {e}")


def connection_event_cb(_reader, event):
    """Callback for connection events only"""
    if "ConnectionAttemptEvent" in event:
        logging.info(f"🔄 Connection Event: {event['ConnectionAttemptEvent']}")
    else:
        logging.info(f"ℹ️ Other Event: {event}")


# -------- COMMAND FUNCTIONS -------- #
def clear_tag_data():
    SEEN_TAGS.clear()
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
    seen_epcs = set()
    while True:
        try:
            tag = TAG_QUEUE.get(timeout=0.2)
            epc = tag["epc"]
            if epc not in seen_epcs:
                seen_epcs.add(epc)
                SEEN_TAGS.append(tag)
                print(f"\n📦 New tag:")
                print(f" - EPC: {epc} | Ch: {tag['channel']} | Seen: {tag['seen_count']}x | Time: {tag['last_seen']}")
        except Empty:
            continue
        except Exception as e:
            print(f"❌ Error in tag processing thread: {e}")
        time.sleep(0.05)


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

    # Create configuration with frequent reporting
    config = LLRPReaderConfig(
        reset_on_connect=True,
        start_inventory=False,
        event_selector={},
        tx_power={1: 200, 2: 200},
        antennas=[1, 2],
        report_every_n_tags=1,
        tag_content_selector={
            'EnableROSpecID': False,
            'EnableSpecIndex': False,
            'EnableInventoryParameterSpecID': False,
            'EnableAntennaID': True,
            'EnableChannelIndex': False,
            'EnablePeakRSSI': True,
            'EnableFirstSeenTimestamp': False,
            'EnableLastSeenTimestamp': True,
            'EnableTagSeenCount': True,
            'EnableAccessSpecID': False,
        }
    )

    # Connect and bind callbacks
    READER = LLRPReaderClient(reader_ip, PORT, config)
    READER.add_tag_report_callback(tag_report_cb)
    READER.add_event_callback(connection_event_cb)
    READER.connect()

    print("✅ Reader connected. Ready for commands.")

    # Launch tag processing thread
    tag_thread = threading.Thread(target=process_tags_console, daemon=True)
    tag_thread.start()

    # Start user loop
    user_interface()

    # Graceful shutdown
    if READER and READER.is_alive():
        READER.llrp.stopPolitely()
        READER.disconnect()
        print("👋 Reader disconnected. Exiting...")


if __name__ == "__main__":
    main()
