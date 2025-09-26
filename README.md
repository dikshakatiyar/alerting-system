# Alerting & Notification Platform

A lightweight alerting and notification system built with Python and Flask that balances admin configurability with user control. The system supports organization-wide, team-specific, and user-specific alerts with recurring reminders.

## Features

### Admin Features
- ✅ Create unlimited alerts with custom visibility
- ✅ Set severity levels (Info, Warning, Critical)
- ✅ Configure start/expiry times
- ✅ Enable/disable reminders
- ✅ Archive and update alerts
- ✅ Filter and view all alerts

### User Features
- ✅ Receive relevant alerts based on visibility
- ✅ Snooze alerts for the current day
- ✅ Mark alerts as read/unread
- ✅ View alert history and status

### System Features
- ✅ In-app notifications (MVP)
- ✅ Recurring reminders every 2 hours
- ✅ Snooze functionality with daily reset
- ✅ Analytics dashboard
- ✅ Extensible architecture

## Quick Start

### Prerequisites
- Python 3.7+
- pip package manager

### Installation

1. **Clone or download the project**
```bash
# Create project directory
mkdir alerting-system
cd alerting-system
```

2. **Create requirements.txt**
```txt
Flask==2.3.3
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the server**
```bash
python alerting_system_complete.py
```

The server will start on `http://localhost:5000`

## API Usage

### Create an Alert
```bash
curl -X POST http://localhost:5000/admin/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "title": "System Maintenance",
    "message": "Scheduled maintenance tonight at 10 PM",
    "severity": "warning",
    "created_by": "user1",
    "visibility_type": "organization",
    "target_ids": []
  }'
```

### Get User Alerts
```bash
curl http://localhost:5000/users/user2/alerts
```

### Snooze an Alert
```bash
curl -X POST http://localhost:5000/users/user2/alerts/1/snooze
```

### Get Analytics
```bash
curl http://localhost:5000/analytics
```

## API Endpoints

### Admin Endpoints
- `POST /admin/alerts` - Create new alert
- `GET /admin/alerts` - List all alerts (filter with `?severity=warning&status=active`)
- `PUT /admin/alerts/<id>` - Update alert
- `POST /admin/alerts/<id>/archive` - Archive alert

### User Endpoints
- `GET /users/<user_id>/alerts` - Get user's alerts
- `POST /users/<user_id>/alerts/<alert_id>/read` - Mark as read
- `POST /users/<user_id>/alerts/<alert_id>/snooze` - Snooze alert

### System Endpoints
- `GET /analytics` - System metrics
- `POST /system/process-reminders` - Process pending reminders
- `GET /health` - Health check

## Sample Data

The system comes with pre-configured sample data:

**Users:**
- `user1` - Admin User (Engineering team)
- `user2` - Engineering User (Engineering team) 
- `user3` - Marketing User (Marketing team)

**Teams:**
- `team1` - Engineering (user1, user2)
- `team2` - Marketing (user3)

## Testing the System

1. **Start the server:**
```bash
python alerting_system_complete.py
```

2. **Create an organization-wide alert:**
```bash
curl -X POST http://localhost:5000/admin/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Welcome Message",
    "message": "Welcome to our new alerting system!",
    "severity": "info",
    "created_by": "user1", 
    "visibility_type": "organization",
    "target_ids": []
  }'
```

3. **Create a team-specific alert:**
```bash
curl -X POST http://localhost:5000/admin/alerts \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Engineering Standup",
    "message": "Daily standup at 10 AM",
    "severity": "warning", 
    "created_by": "user1",
    "visibility_type": "team",
    "target_ids": ["team1"]
  }'
```

4. **Check user alerts:**
```bash
curl http://localhost:5000/users/user2/alerts
```

## Architecture

The system follows clean OOP design principles:

- **Strategy Pattern** for notification channels
- **State Pattern** for alert status management  
- **Factory Pattern** for visibility configurations
- **Single Responsibility Principle** for modularity

### Key Components

- `AlertManager` - Alert CRUD operations and visibility management
- `NotificationDelivery` - Multi-channel notification delivery
- `UserAlertStateManager` - User preference and state tracking
- `ReminderScheduler` - Automated reminder processing
- `AnalyticsEngine` - System metrics and reporting

## Extensibility

The system is designed to be easily extended:

### Adding New Notification Channels
```python
class PushChannel(NotificationChannel):
    def send(self, alert: Alert, user_id: str) -> bool:
        # Implement push notification logic
        pass
```

### Custom Reminder Frequencies
```python
alert = system.create_alert(
    # ... other parameters ...
    reminder_frequency=timedelta(hours=4)  # Custom frequency
)
```

### New Visibility Types
```python
class RoleVisibility(VisibilityConfig):
    def get_target_users(self, user_repository: 'UserRepository') -> Set[str]:
        # Target users by role
        pass
```

## Future Enhancements

- Email & SMS notification channels
- Customizable reminder frequencies
- Scheduled alerts (cron-like)
- Role-based access control
- Push notification integration
- Database persistence (currently in-memory)

## Development

### Running Tests
```bash
# Create a test script
echo "from alerting_system_complete import AlertingSystem, Severity; system = AlertingSystem(); print('System initialized successfully')" > test.py
python test.py
```

### Project Structure
```
alerting-system/
├── alerting_system_complete.py  # Main application
├── requirements.txt             # Dependencies
└── README.md                   # This file
```

## Support

For issues or questions, please check the code comments or refer to the extensive inline documentation.
