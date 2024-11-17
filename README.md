# Honeywell Home Thermostat Controller

A Python script to remotely control and monitor your Honeywell home thermostat's temperature settings. Works with the international version of the Total Connect Comfort system.

## Features

- Set temperature remotely via command line
- Automatic temperature hold until 22:50
- Push notifications via Pushover when temperature setpoint changes
- Secure credential management using environment variables
- Support for Celsius temperature units

## Prerequisites

- Python 3.11 or higher
- Honeywell Total Connect Comfort account
- Pushover account (for notifications)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/iot_honeywellhome.git
cd iot_honeywellhome
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your credentials:
```
HONEYWELL_EMAIL=your_email@example.com
HONEYWELL_PASSWORD=your_password
PUSHOVER_USER_KEY=your_pushover_user_key
PUSHOVER_API_TOKEN=your_pushover_api_token
```

## Usage

Set the temperature (in Celsius):
```bash
./set_thermostat.py --temperature 21.5
```

The script will:
1. Show the current room temperature
2. Set the new temperature until 22:50
3. Send a Pushover notification if the setpoint changes
4. Verify the change was successful

## Environment Variables

- `HONEYWELL_EMAIL`: Your Total Connect Comfort email
- `HONEYWELL_PASSWORD`: Your Total Connect Comfort password
- `PUSHOVER_USER_KEY`: Your Pushover user key
- `PUSHOVER_API_TOKEN`: Your Pushover application token

## Notes

- Temperature changes are held until 22:50
- The script uses the international version of the Total Connect Comfort API
- Notifications are sent only when the temperature setpoint changes by more than 0.1°C

## License

MIT License