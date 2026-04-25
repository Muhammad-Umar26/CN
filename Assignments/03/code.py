import time
import random
import threading
import sys

# ==========================================
# CONFIGURATION (Editable for Demo)
# ==========================================
PROTOCOL_MODE = "SR"   # Change to "RDT3.0", "GBN", or "SR"
TOTAL_PACKETS = 10     # Configurable count of packets
PACKET_SIZE = 512      # Configurable size of packet (bytes)
TIMEOUT = 1.0          # Fixed timeout period for retransmissions
WINDOW_SIZE = 4        # Window size for GBN and SR

# Network Error Probabilities
PROB_LOSS = 0.15
PROB_CORRUPT = 0.10
PROB_DELAY = 0.10

# ==========================================
# PACKET & NETWORK CLASSES
# ==========================================
class Packet:
    def __init__(self, seq_num, data, is_ack=False):
        self.seq_num = seq_num
        self.data = data
        self.is_ack = is_ack
        self.is_corrupted = False
        # Pad data to simulate configurable packet size
        if not is_ack and data:
            self.payload = data.ljust(PACKET_SIZE, '*')
        else:
            self.payload = data

    def corrupt(self):
        self.is_corrupted = True

class Network:
    def __init__(self, receiver):
        self.receiver = receiver

    def send_to_receiver(self, packet):
        packet.is_corrupted = False 
        
        if random.random() < PROB_LOSS:
            print(f"[Network] Packet {packet.seq_num} LOST.")
            return

        if random.random() < PROB_CORRUPT:
            print(f"[Network] Packet {packet.seq_num} CORRUPTED.")
            packet.corrupt()

        if random.random() < PROB_DELAY:
            delay = random.uniform(0.5, 1.5)
            print(f"[Network] Packet {packet.seq_num} DELAYED by {delay:.2f}s.")
            # Spawning a thread for delay so it doesn't block other packets
            threading.Timer(delay, self.receiver.receive, args=[packet]).start()
            return

        self.receiver.receive(packet)

    def send_to_sender(self, sender, ack_packet):
        ack_packet.is_corrupted = False
        
        # Simulating possible loss/corruption of ACKs too
        if random.random() < PROB_LOSS:
            print(f"[Network] ACK {ack_packet.seq_num} LOST.")
            return
            
        sender.receive_ack(ack_packet)

# ==========================================
# RDT 3.0 (Stop-and-Wait)
# ==========================================
class RDTReceiver:
    def __init__(self, network):
        self.expected_seq = 0
        self.network = network
        self.sender = None

    def receive(self, packet):
        if not packet.is_corrupted and packet.seq_num == self.expected_seq:
            print(f"[Receiver] Received Packet {packet.seq_num}, sending ACK {packet.seq_num}")
            ack = Packet(self.expected_seq, "ACK", is_ack=True)
            self.expected_seq = 1 - self.expected_seq
            self.network.send_to_sender(self.sender, ack)
        else:
            print(f"[Receiver] Error/Mismatch in Packet {packet.seq_num}. Resending ACK {1 - self.expected_seq}")
            ack = Packet(1 - self.expected_seq, "ACK", is_ack=True)
            self.network.send_to_sender(self.sender, ack)

class RDTSender:
    def __init__(self, network):
        self.network = network
        self.seq_num = 0
        self.waiting_for_ack = False
        self.timer = None

    def send_data(self, data):
        packet = Packet(self.seq_num, data)
        print(f"\n[Sender] Sending Packet {packet.seq_num}")
        self.waiting_for_ack = True
        self.start_timer(packet)
        self.network.send_to_receiver(packet)

        while self.waiting_for_ack:
            time.sleep(0.1)

    def start_timer(self, packet):
        if self.timer: self.timer.cancel()
        self.timer = threading.Timer(TIMEOUT, self.timeout, args=[packet])
        self.timer.start()

    def timeout(self, packet):
        print(f"[Sender] TIMEOUT! Retransmitting Packet {packet.seq_num}")
        self.start_timer(packet)
        self.network.send_to_receiver(packet)

    def receive_ack(self, ack_packet):
        if ack_packet.seq_num == self.seq_num and not ack_packet.is_corrupted:
            print(f"[Sender] Received ACK {ack_packet.seq_num}. Moving on.")
            self.waiting_for_ack = False
            if self.timer: self.timer.cancel()
            self.seq_num = 1 - self.seq_num

# ==========================================
# GO-BACK-N (GBN)
# ==========================================
class GBNReceiver:
    def __init__(self, network):
        self.expected_seq = 0
        self.network = network
        self.sender = None

    def receive(self, packet):
        if not packet.is_corrupted and packet.seq_num == self.expected_seq:
            print(f"[Receiver] Received Packet {packet.seq_num}, sending ACK {packet.seq_num}")
            ack = Packet(self.expected_seq, "ACK", is_ack=True)
            self.network.send_to_sender(self.sender, ack)
            self.expected_seq += 1
        else:
            # Send cumulative ACK for the last correctly received packet
            ack_seq = self.expected_seq - 1
            if ack_seq >= 0:
                print(f"[Receiver] Received Packet {packet.seq_num}, discarded, resending duplicate ACK {ack_seq}")
                ack = Packet(ack_seq, "ACK", is_ack=True)
                self.network.send_to_sender(self.sender, ack)

class GBNSender:
    def __init__(self, network):
        self.network = network
        self.base = 0
        self.next_seq_num = 0
        self.packets = []
        self.timer = None

    def send_data(self, data_list):
        for data in data_list:
            self.packets.append(Packet(len(self.packets), data))

        while self.base < len(self.packets):
            while self.next_seq_num < self.base + WINDOW_SIZE and self.next_seq_num < len(self.packets):
                print(f"[Sender] Sending Packet {self.next_seq_num}")
                self.network.send_to_receiver(self.packets[self.next_seq_num])
                if self.base == self.next_seq_num:
                    self.start_timer()
                self.next_seq_num += 1
            time.sleep(0.5)

    def start_timer(self):
        if self.timer: self.timer.cancel()
        self.timer = threading.Timer(TIMEOUT, self.timeout)
        self.timer.start()

    def timeout(self):
        if self.base >= len(self.packets):
            return
        
        print(f"[Sender] TIMEOUT! Go-Back-N resetting to {self.base}")
        self.start_timer()
        for i in range(self.base, self.next_seq_num):
            print(f"[Sender] Retransmitting Packet {i}")
            self.network.send_to_receiver(self.packets[i])

    def receive_ack(self, ack_packet):
        if not ack_packet.is_corrupted:
            print(f"[Sender] Received Cumulative ACK {ack_packet.seq_num}")
            self.base = ack_packet.seq_num + 1
            if self.base == self.next_seq_num:
                if self.timer: self.timer.cancel()
            else:
                self.start_timer()

# ==========================================
# SELECTIVE REPEAT (SR)
# ==========================================
class SRReceiver:
    def __init__(self, network):
        self.base = 0
        self.network = network
        self.sender = None
        self.buffer = {}

    def receive(self, packet):
        if packet.is_corrupted or packet.seq_num < self.base - WINDOW_SIZE or packet.seq_num >= self.base + WINDOW_SIZE:
            return # Ignore packets that are too old or too new

        print(f"[Receiver] Received Packet {packet.seq_num}", end="")
        
        if self.base == packet.seq_num:
            if len(self.buffer) > 0:
                print(f"; delivering Packet {packet.seq_num}", end="")
                self.base += 1
                while self.base in self.buffer:
                    print(f", Packet {self.base}", end="")
                    del self.buffer[self.base]
                    self.base += 1
                print("; ", end="")
            else:
                print(", ", end="")
                self.base += 1
        elif self.base < packet.seq_num:
            self.buffer[packet.seq_num] = packet.payload
            print(", buffer, ", end="")
        else:
            print(", ", end="")

        print(f"sending ACK {packet.seq_num}")
        ack = Packet(packet.seq_num, "ACK", is_ack=True)
        self.network.send_to_sender(self.sender, ack)

class SRSender:
    def __init__(self, network):
        self.network = network
        self.base = 0
        self.next_seq_num = 0
        self.packets = []
        self.timers = {}
        self.acked = {}

    def send_data(self, data_list):
        for data in data_list:
            self.packets.append(Packet(len(self.packets), data))
            self.acked[len(self.packets) - 1] = False

        while self.base < len(self.packets):
            while self.next_seq_num < self.base + WINDOW_SIZE and self.next_seq_num < len(self.packets):
                print(f"[Sender] Sending Packet {self.next_seq_num}")
                self.network.send_to_receiver(self.packets[self.next_seq_num])
                self.start_timer(self.next_seq_num)
                self.next_seq_num += 1
            time.sleep(0.5)

    def start_timer(self, seq_num):
        if seq_num in self.timers and self.timers[seq_num]:
            self.timers[seq_num].cancel()
        self.timers[seq_num] = threading.Timer(TIMEOUT, self.timeout, args=[seq_num])
        self.timers[seq_num].start()

    def timeout(self, seq_num):
        if not self.acked[seq_num]:
            print(f"[Sender] TIMEOUT! Retransmitting ONLY Packet {seq_num}")
            self.network.send_to_receiver(self.packets[seq_num])
            self.start_timer(seq_num)

    def receive_ack(self, ack_packet):
        if not ack_packet.is_corrupted:
            seq = ack_packet.seq_num
            print(f"[Sender] Received ACK {seq}")
            self.acked[seq] = True
            if seq in self.timers and self.timers[seq]:
                self.timers[seq].cancel()
            
            # Advance base to oldest unacknowledged packet
            while self.base in self.acked and self.acked[self.base]:
                self.base += 1

# ==========================================
# MAIN SIMULATION RUNNER
# ==========================================
if __name__ == "__main__":
    print(f"=== Starting Simulation: {PROTOCOL_MODE} Mode ===")
    print(f"Total Packets: {TOTAL_PACKETS}, Packet Size: {PACKET_SIZE} bytes, Timeout: {TIMEOUT}s")
    print("-" * 50)
    
    # Generate data payload
    data_list = [f"Data_Payload_{i}" for i in range(TOTAL_PACKETS)]
    
    if PROTOCOL_MODE == "RDT3.0":
        network = Network(None)
        receiver = RDTReceiver(network)
        network.receiver = receiver
        sender = RDTSender(network)
        receiver.sender = sender
        
        for data in data_list:
            sender.send_data(data)
            
    elif PROTOCOL_MODE == "GBN":
        network = Network(None)
        receiver = GBNReceiver(network)
        network.receiver = receiver
        sender = GBNSender(network)
        receiver.sender = sender
        
        sender.send_data(data_list)
        
    elif PROTOCOL_MODE == "SR":
        network = Network(None)
        receiver = SRReceiver(network)
        network.receiver = receiver
        sender = SRSender(network)
        receiver.sender = sender
        
        sender.send_data(data_list)
        
    # Wait briefly to ensure trailing ACKs complete processing
    time.sleep(TIMEOUT + 1)
    print("\n[Simulation Complete] All packets successfully delivered!")