# wireless_connect.py (MicroPython)

import network
import bluetooth  # Requires BLE support on the board

wifi_available = False
bluetooth_available = False

# Check for WiFi availability at import time
try:
    wlan = network.WLAN(network.STA_IF)
    wlan.active(False)  # Start disabled. Enable later if requested.
    wifi_available = True
    del wlan  # Clean up the temporary object
except Exception as e:
    print("WiFi not available at import:", e)
    wifi_available = False


# Check for Bluetooth availability at import time
try:
    ble = bluetooth.BLE()
    ble.active(False)  # Start disabled. Enable later if requested.
    bluetooth_available = True
    del ble  # Clean up the temporary object
except Exception as e:
    print("Bluetooth not available at import:", e)
    bluetooth_available = False


class WirelessConnector:
    def __init__(self, wifi_ssid=None, wifi_password=None):
        """
        Initializes the WirelessConnector.

        Args:
            wifi_ssid (str, optional): WiFi SSID. Defaults to None.
            wifi_password (str, optional): WiFi password. Defaults to None.
        """
        self.wifi_ssid = wifi_ssid
        self.wifi_password = wifi_password
        self.wlan = network.WLAN(network.STA_IF) if wifi_available else None  # WiFi interface object
        self.ble = bluetooth.BLE() if bluetooth_available else None   # Bluetooth interface object
        self.wifi_enabled = wifi_available
        self.bluetooth_enabled = bluetooth_available

    def enable_wifi(self):
        """Enables and connects to WiFi if credentials are provided."""
        if not self.wifi_enabled:
            print("WiFi not available on this hardware.")
            return False

        if not self.wifi_ssid or not self.wifi_password:
            print("WiFi SSID and password must be provided.")
            return False

        if self.wlan.isconnected():
            print("WiFi already connected.")
            return True

        self.wlan.active(True)
        self.wlan.connect(self.wifi_ssid, self.wifi_password)

        import time
        max_wait = 10  # Seconds to wait for connection
        while max_wait > 0:
            if self.wlan.status() < 0 or self.wlan.status() >= 3:
                break
            max_wait -= 1
            print('waiting for connection...')
            time.sleep(1)

        if self.wlan.status() != 3:
            print('WiFi connection failed! Status:', self.wlan.status())
            return False
        else:
            print('WiFi connected')
            status = self.wlan.ifconfig()
            print('IP address  = ' + status[0])
            print('Subnet mask = ' + status[1])
            print('Gateway     = ' + status[2])
            print('DNS Server  = ' + status[3])
            return True

    def disable_wifi(self):
        """Disables WiFi."""
        if self.wifi_enabled and self.wlan.active():
            self.wlan.disconnect()
            self.wlan.active(False)
            print("WiFi disabled.")

    def enable_bluetooth(self):
        """Enables Bluetooth."""
        if not self.bluetooth_enabled:
            print("Bluetooth not available on this hardware.")
            return False

        if not self.ble.active():
            self.ble.active(True)
            print("Bluetooth enabled.")
        else:
            print("Bluetooth already enabled.")
        return True

    def disable_bluetooth(self):
        """Disables Bluetooth."""
        if self.bluetooth_enabled and self.ble.active():
            self.ble.active(False)
            print("Bluetooth disabled.")

    def scan_bluetooth(self, duration_ms=2000):
        """Scans for nearby Bluetooth devices."""
        if not self.bluetooth_enabled:
            print("Bluetooth not available on this hardware.")
            return None

        import bluetooth
        bluetooth_devices = []
        try:
            self.ble.active(True)
            self.ble.gap_scan(duration_ms, 128, 128)
            adv_data = self.ble.gap_scan(duration_ms, 128, 128)  # Scan again to get results
            for result in adv_data:
                addr_type, addr, adv_type, rssi, adv_data = result
                name = bluetooth.decode_name(adv_data)
                if name:
                    bluetooth_devices.append((name, addr, rssi))
            self.ble.active(False)  # Stop scanning

        except Exception as e:
            print("Error scanning for Bluetooth devices:", e)
            self.ble.active(False) # Ensure BT is disabled on error
            return None

        return bluetooth_devices

    def is_wifi_available(self):
        """Returns True if WiFi is available on this hardware."""
        return self.wifi_enabled

    def is_bluetooth_available(self):
        """Returns True if Bluetooth is available on this hardware."""
        return self.bluetooth_enabled


# Example Usage (in your main.py or other file)
if __name__ == "__main__":
    # Replace with your actual WiFi credentials
    WIFI_SSID = "your_wifi_ssid"
    WIFI_PASSWORD = "your_wifi_password"

    # Create an instance of the WirelessConnector
    connector = WirelessConnector(wifi_ssid=WIFI_SSID, wifi_password=WIFI_PASSWORD)

    # Check for availability
    if connector.is_wifi_available():
        print("WiFi is available on this board.")
        # Enable WiFi
        if connector.enable_wifi():
            print("Successfully connected to WiFi!")
        else:
            print("Failed to connect to WiFi.")

    else:
        print("WiFi is not available on this board.")

    if connector.is_bluetooth_available():
        print("Bluetooth is available on this board.")
        # Enable Bluetooth
        connector.enable_bluetooth()
        # Scan for devices
        print("Scanning for Bluetooth devices...")
        devices = connector.scan_bluetooth(duration_ms=5000)  # Scan for 5 seconds
        if devices:
            print("Found Bluetooth devices:")
            for name, addr, rssi in devices:
                print(f"  Name: {name}, Address: {addr}, RSSI: {rssi}")
        else:
            print("No Bluetooth devices found.")

        #Disable Bluetooth
        connector.disable_bluetooth()

    else:
        print("Bluetooth is not available on this board.")

    if connector.is_wifi_available():
        connector.disable_wifi()