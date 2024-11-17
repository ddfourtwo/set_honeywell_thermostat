#!/Users/daniel/Documents/GitHub/iot_honeywellhome/.venv/bin/python3

import argparse
import json
import os
import requests
import sys
from typing import Dict, Optional, Tuple
import datetime
from dotenv import load_dotenv
import time
from pushover_complete import PushoverAPI

# Load environment variables from .env file
load_dotenv()

class HoneywellThermostat:
    BASE_URL = "https://international.mytotalconnectcomfort.com"
    
    def __init__(self, email: str, password: str, pushover_client: Optional[PushoverAPI] = None):
        self.email = email
        self.password = password
        self.pushover = pushover_client
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json; charset=UTF-8'
        })
        self.location_id = None
        self.zone_id = None

    def send_notification(self, message: str, title: str = "Thermostat Update"):
        """Send a notification via Pushover."""
        if self.pushover:
            try:
                self.pushover.send_message(user=os.getenv('PUSHOVER_USER_KEY'), message=message, title=title)
            except Exception as e:
                print(f"Failed to send notification: {e}")

    def login(self) -> bool:
        """Login to the Honeywell service."""
        login_url = f"{self.BASE_URL}/api/accountApi/login"
        
        data = {
            "EmailAddress": self.email,
            "Password": self.password,
            "RememberMe": False,
            "IsServiceStatusReturned": True,
            "ApiActive": True,
            "ApiDown": False,
            "RedirectUrl": "",
            "events": [],
            "formErrors": []
        }
        
        try:
            print(f"Attempting login for {self.email}...")
            response = self.session.post(login_url, json=data)
            print(f"Login response status: {response.status_code}")
            print(f"Login response: {response.text}")
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Login failed: {e}")
            return False

    def get_locations(self) -> Optional[str]:
        """Get the first location ID."""
        locations_url = f"{self.BASE_URL}/api/locationsapi/getlocations"
        
        try:
            print("Fetching locations...")
            response = self.session.get(locations_url)
            print(f"Locations response status: {response.status_code}")
            print(f"Locations response: {response.text}")
            response.raise_for_status()
            data = response.json()
            
            # Extract locations from the new nested structure
            locations = data.get('Content', {}).get('Locations', [])
            
            if locations and len(locations) > 0:
                self.location_id = str(locations[0].get('Id'))  # Note: 'Id' instead of 'id'
                print(f"Found location ID: {self.location_id}")
                
                # Also get the zone ID from the location data
                zones = locations[0].get('Zones', [])
                if zones and len(zones) > 0:
                    self.zone_id = str(zones[0].get('Id'))  # Note: 'Id' instead of 'id'
                    print(f"Found zone ID: {self.zone_id}")
                
                return self.location_id
        except requests.exceptions.RequestException as e:
            print(f"Failed to get locations: {e}")
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"Failed to parse location data: {e}")
        
        return None

    def get_system_info(self) -> Optional[Dict]:
        """Get the system information for the location."""
        if not self.location_id:
            print("No location ID available")
            return None
            
        # We don't need to make another API call since we already have the zone ID
        return {"zones": [{"id": self.zone_id}]} if self.zone_id else None

    def get_zone_status(self) -> Optional[Dict]:
        """Get the current zone status including temperatures."""
        if not self.zone_id:
            print("No zone ID available")
            return None
            
        # Get locations again as it contains the current temperature info
        try:
            response = self.session.get(f"{self.BASE_URL}/api/locationsapi/getlocations")
            response.raise_for_status()
            data = response.json()
            
            locations = data.get('Content', {}).get('Locations', [])
            if locations and len(locations) > 0:
                zones = locations[0].get('Zones', [])
                if zones and len(zones) > 0:
                    zone = zones[0]
                    return {
                        'indoorTemperature': zone.get('Temperature'),
                        'heatSetpoint': zone.get('TargetHeatTemperature')
                    }
        except requests.exceptions.RequestException as e:
            print(f"Failed to get zone status: {e}")
        except json.JSONDecodeError as e:
            print(f"Failed to parse zone status: {e}")
        
        return None

    def get_current_temperature(self) -> Tuple[Optional[float], Optional[float]]:
        """Get current temperature and setpoint."""
        zone_status = self.get_zone_status()
        if not zone_status:
            return None, None
            
        try:
            current_temp = float(zone_status.get('indoorTemperature', 0))
            setpoint = float(zone_status.get('heatSetpoint', 0))
            return current_temp, setpoint
        except (ValueError, TypeError, KeyError) as e:
            print(f"Failed to parse temperature data: {e}")
            return None, None

    def set_temperature(self, temp_celsius: float) -> bool:
        """Set the target temperature in Celsius."""
        if not self.zone_id:
            print("No zone ID available")
            return False

        # Get current setpoint before change
        _, current_setpoint = self.get_current_temperature()
        
        # Get current time and calculate end time (22:00 by default)
        now = datetime.datetime.now()
        
        # Prepare the temperature update payload with the new structure
        payload = {
            "zoneId": self.zone_id,
            "heatTemperature": str(temp_celsius),  # API expects string
            "hotWaterStateIsOn": False,
            "isPermanent": False,
            "setUntilHours": "22",  # Default to 22:00
            "setUntilMinutes": "50",
            "locationTimeOffsetMinutes": 60,  # Timezone offset
            "isFollowingSchedule": False
        }
        
        set_temp_url = f"{self.BASE_URL}/api/ZonesApi/SetZoneTemperature"
        
        try:
            response = self.session.post(set_temp_url, json=payload)
            response.raise_for_status()
            print(f"Successfully set temperature to {temp_celsius}°C until 22:50")
            
            # Send notification if setpoint has changed
            if current_setpoint is not None and abs(current_setpoint - temp_celsius) > 0.1:
                self.send_notification(
                    f"Temperature setpoint changed from {current_setpoint}°C to {temp_celsius}°C until 22:50",
                    "Thermostat Update"
                )
            
            return True
        except requests.exceptions.RequestException as e:
            print(f"Failed to set temperature: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Control Honeywell Thermostat')
    parser.add_argument('--temperature', type=float, required=True, help='Target temperature in Celsius')
    
    args = parser.parse_args()
    
    # Get credentials from environment variables
    email = os.getenv('HONEYWELL_EMAIL')
    password = os.getenv('HONEYWELL_PASSWORD')
    pushover_token = os.getenv('PUSHOVER_API_TOKEN')
    
    if not email or not password:
        print("Error: Please set HONEYWELL_EMAIL and HONEYWELL_PASSWORD in your .env file")
        sys.exit(1)
    
    # Initialize Pushover client if credentials are available
    pushover_client = None
    if pushover_token:
        pushover_client = PushoverAPI(pushover_token)
    
    thermostat = HoneywellThermostat(email, password, pushover_client)
    
    if not thermostat.login():
        sys.exit(1)
        
    if not thermostat.get_locations():
        print("Failed to get location information")
        sys.exit(1)
        
    if not thermostat.get_system_info():
        print("Failed to get system information")
        sys.exit(1)
        
    # Get current temperature before change
    current_temp, current_setpoint = thermostat.get_current_temperature()
    if current_temp is not None and current_setpoint is not None:
        print(f"Current temperature: {current_temp}°C")
        print(f"Current setpoint: {current_setpoint}°C")
    
    # Set new temperature
    if not thermostat.set_temperature(args.temperature):
        print("Failed to set temperature")
        sys.exit(1)
    
    # Wait a moment for the change to take effect
    print("Waiting for temperature change to take effect...")
    time.sleep(2)
    
    # Get temperature after change
    new_temp, new_setpoint = thermostat.get_current_temperature()
    if new_temp is not None and new_setpoint is not None:
        print(f"New temperature: {new_temp}°C")
        print(f"New setpoint: {new_setpoint}°C")
        
        if abs(new_setpoint - args.temperature) > 0.1:
            print("Warning: New setpoint doesn't match requested temperature!")

if __name__ == "__main__":
    main()