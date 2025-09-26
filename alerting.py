# alerting_system_complete.py
from flask import Flask, request, jsonify
from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Set, Optional, Dict
import json

# ===== ENUMS & DATA MODELS =====
class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class DeliveryType(Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"

class AlertStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    ARCHIVED = "archived"

class NotificationStatus(Enum):
    UNREAD = "unread"
    READ = "read"
    SNOOZED = "snoozed"

@dataclass
class User:
    id: str
    name: str
    email: str
    team_id: str

@dataclass
class Team:
    id: str
    name: str
    member_ids: Set[str]

@dataclass
class Alert:
    id: str
    title: str
    message: str
    severity: Severity
    delivery_type: DeliveryType
    created_by: str
    visibility_config: 'VisibilityConfig'
    start_time: datetime
    expiry_time: Optional[datetime]
    reminder_frequency: timedelta = timedelta(hours=2)
    status: AlertStatus = AlertStatus.ACTIVE
    reminders_enabled: bool = True

    def is_active(self) -> bool:
        now = datetime.now()
        if self.status != AlertStatus.ACTIVE:
            return False
        if now < self.start_time:
            return False
        if self.expiry_time and now > self.expiry_time:
            return False
        return True

@dataclass
class UserAlertState:
    user_id: str
    alert_id: str
    status: NotificationStatus
    last_reminder_sent: Optional[datetime] = None
    snoozed_until: Optional[datetime] = None
    read_at: Optional[datetime] = None
    
    def should_receive_reminder(self, alert: Alert) -> bool:
        if self.status == NotificationStatus.SNOOZED:
            if self.snoozed_until and datetime.now() > self.snoozed_until:
                self.status = NotificationStatus.UNREAD
                self.snoozed_until = None
            else:
                return False
        
        if self.status == NotificationStatus.READ:
            return False
            
        if not self.last_reminder_sent:
            return True
            
        time_since_last = datetime.now() - self.last_reminder_sent
        return time_since_last >= alert.reminder_frequency
    
    def mark_read(self):
        self.status = NotificationStatus.READ
        self.read_at = datetime.now()
    
    def snooze_until_tomorrow(self):
        tomorrow = datetime.now() + timedelta(days=1)
        self.snoozed_until = tomorrow.replace(hour=0, minute=0, second=0)
        self.status = NotificationStatus.SNOOZED

@dataclass
class AlertAnalytics:
    total_alerts: int
    active_alerts: int
    expired_alerts: int
    alerts_by_severity: Dict[Severity, int]
    delivery_stats: Dict[str, int]

# ===== VISIBILITY CONFIGURATIONS =====
class VisibilityConfig(ABC):
    @abstractmethod
    def get_target_users(self, user_repository: 'UserRepository') -> Set[str]:
        pass

class OrganizationVisibility(VisibilityConfig):
    def get_target_users(self, user_repository: 'UserRepository') -> Set[str]:
        return set(user_repository.get_all_user_ids())

class TeamVisibility(VisibilityConfig):
    def __init__(self, team_ids: Set[str]):
        self.team_ids = team_ids
    
    def get_target_users(self, user_repository: 'UserRepository') -> Set[str]:
        target_users = set()
        for team_id in self.team_ids:
            team = user_repository.get_team(team_id)
            if team:
                target_users.update(team.member_ids)
        return target_users

class UserVisibility(VisibilityConfig):
    def __init__(self, user_ids: Set[str]):
        self.user_ids = user_ids
    
    def get_target_users(self, user_repository: 'UserRepository') -> Set[str]:
        return self.user_ids

class VisibilityFactory:
    @staticmethod
    def create_visibility(visibility_type: str, target_ids: Set[str]) -> VisibilityConfig:
        if visibility_type == "organization":
            return OrganizationVisibility()
        elif visibility_type == "team":
            return TeamVisibility(target_ids)
        elif visibility_type == "user":
            return UserVisibility(target_ids)
        else:
            raise ValueError(f"Unknown visibility type: {visibility_type}")

# ===== NOTIFICATION CHANNELS =====
class NotificationChannel(ABC):
    @abstractmethod
    def send(self, alert: Alert, user_id: str) -> bool:
        pass

class InAppChannel(NotificationChannel):
    def send(self, alert: Alert, user_id: str) -> bool:
        print(f"In-App notification sent to user {user_id}: {alert.title}")
        return True

class EmailChannel(NotificationChannel):
    def send(self, alert: Alert, user_id: str) -> bool:
        print(f"Email sent to user {user_id}: {alert.title}")
        return True

class NotificationDelivery:
    def __init__(self):
        self._channels = {
            DeliveryType.IN_APP: InAppChannel(),
            DeliveryType.EMAIL: EmailChannel()
        }
    
    def deliver(self, alert: Alert, user_id: str) -> bool:
        channel = self._channels.get(alert.delivery_type)
        if channel:
            return channel.send(alert, user_id)
        return False

# ===== REPOSITORY & MANAGEMENT =====
class UserRepository:
    def __init__(self):
        self.users = {
            "user1": User("user1", "Admin User", "admin@company.com", "team1"),
            "user2": User("user2", "Engineering User", "eng@company.com", "team1"),
            "user3": User("user3", "Marketing User", "marketing@company.com", "team2"),
        }
        self.teams = {
            "team1": Team("team1", "Engineering", {"user1", "user2"}),
            "team2": Team("team2", "Marketing", {"user3"}),
        }
    
    def get_user(self, user_id: str) -> Optional[User]:
        return self.users.get(user_id)
    
    def get_team(self, team_id: str) -> Optional[Team]:
        return self.teams.get(team_id)
    
    def get_all_user_ids(self) -> Set[str]:
        return set(self.users.keys())

class AlertManager:
    def __init__(self, user_repository: 'UserRepository'):
        self.alerts: Dict[str, Alert] = {}
        self.user_repository = user_repository
    
    def create_alert(self, title: str, message: str, severity: Severity, 
                    delivery_type: DeliveryType, created_by: str,
                    visibility_type: str, target_ids: Set[str],
                    start_time: datetime, expiry_time: Optional[datetime] = None,
                    reminder_frequency: timedelta = timedelta(hours=2)) -> Alert:
        
        visibility_config = VisibilityFactory.create_visibility(visibility_type, target_ids)
        
        alert = Alert(
            id=str(len(self.alerts) + 1),
            title=title,
            message=message,
            severity=severity,
            delivery_type=delivery_type,
            created_by=created_by,
            visibility_config=visibility_config,
            start_time=start_time,
            expiry_time=expiry_time,
            reminder_frequency=reminder_frequency
        )
        
        self.alerts[alert.id] = alert
        return alert
    
    def update_alert(self, alert_id: str, **kwargs) -> Optional[Alert]:
        if alert_id not in self.alerts:
            return None
        
        alert = self.alerts[alert_id]
        for key, value in kwargs.items():
            if hasattr(alert, key):
                setattr(alert, key, value)
        
        return alert
    
    def archive_alert(self, alert_id: str) -> bool:
        if alert_id in self.alerts:
            self.alerts[alert_id].status = AlertStatus.ARCHIVED
            return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        return [alert for alert in self.alerts.values() if alert.is_active()]
    
    def get_alerts_for_user(self, user_id: str) -> List[Alert]:
        user_alerts = []
        for alert in self.get_active_alerts():
            target_users = alert.visibility_config.get_target_users(self.user_repository)
            if user_id in target_users:
                user_alerts.append(alert)
        return user_alerts

class UserAlertStateManager:
    def __init__(self):
        self.user_states: Dict[str, Dict[str, UserAlertState]] = {}
    
    def get_state(self, user_id: str, alert_id: str) -> UserAlertState:
        if user_id not in self.user_states:
            self.user_states[user_id] = {}
        if alert_id not in self.user_states[user_id]:
            self.user_states[user_id][alert_id] = UserAlertState(
                user_id=user_id, 
                alert_id=alert_id, 
                status=NotificationStatus.UNREAD
            )
        return self.user_states[user_id][alert_id]
    
    def update_state(self, state: UserAlertState):
        if state.user_id not in self.user_states:
            self.user_states[state.user_id] = {}
        self.user_states[state.user_id][state.alert_id] = state

class ReminderScheduler:
    def __init__(self, alert_manager: AlertManager, delivery: NotificationDelivery, state_manager: UserAlertStateManager):
        self.alert_manager = alert_manager
        self.delivery = delivery
        self.state_manager = state_manager
    
    def process_reminders(self):
        active_alerts = self.alert_manager.get_active_alerts()
        
        for alert in active_alerts:
            if not alert.reminders_enabled:
                continue
                
            target_users = alert.visibility_config.get_target_users(self.alert_manager.user_repository)
            
            for user_id in target_users:
                user_state = self.state_manager.get_state(user_id, alert.id)
                
                if user_state.should_receive_reminder(alert):
                    if self.delivery.deliver(alert, user_id):
                        user_state.last_reminder_sent = datetime.now()
                        self.state_manager.update_state(user_state)

class AnalyticsEngine:
    def __init__(self, alert_manager: AlertManager, state_manager: UserAlertStateManager):
        self.alert_manager = alert_manager
        self.state_manager = state_manager
    
    def get_system_analytics(self) -> AlertAnalytics:
        alerts = list(self.alert_manager.alerts.values())
        active_alerts = self.alert_manager.get_active_alerts()
        
        severity_counts = {severity: 0 for severity in Severity}
        for alert in alerts:
            severity_counts[alert.severity] += 1
        
        delivered = 0
        read = 0
        snoozed = 0
        
        for user_states in self.state_manager.user_states.values():
            for state in user_states.values():
                delivered += 1
                if state.status == NotificationStatus.READ:
                    read += 1
                elif state.status == NotificationStatus.SNOOZED:
                    snoozed += 1
        
        return AlertAnalytics(
            total_alerts=len(alerts),
            active_alerts=len(active_alerts),
            expired_alerts=len([a for a in alerts if a.status == AlertStatus.EXPIRED]),
            alerts_by_severity=severity_counts,
            delivery_stats={
                "delivered": delivered,
                "read": read,
                "snoozed": snoozed
            }
        )

# ===== MAIN SYSTEM =====
class AlertingSystem:
    def __init__(self):
        self.user_repository = UserRepository()
        self.alert_manager = AlertManager(self.user_repository)
        self.delivery = NotificationDelivery()
        self.state_manager = UserAlertStateManager()
        self.scheduler = ReminderScheduler(self.alert_manager, self.delivery, self.state_manager)
        self.analytics = AnalyticsEngine(self.alert_manager, self.state_manager)
    
    def create_alert(self, title: str, message: str, severity: Severity, 
                    created_by: str, visibility_type: str, target_ids: Set[str],
                    **kwargs) -> Alert:
        return self.alert_manager.create_alert(
            title=title,
            message=message,
            severity=severity,
            delivery_type=DeliveryType.IN_APP,
            created_by=created_by,
            visibility_type=visibility_type,
            target_ids=target_ids,
            **kwargs
        )
    
    def list_alerts(self, filters: Optional[Dict] = None) -> List[Alert]:
        alerts = list(self.alert_manager.alerts.values())
        if filters:
            filtered_alerts = []
            for alert in alerts:
                matches = True
                if 'severity' in filters and alert.severity != filters['severity']:
                    matches = False
                if 'status' in filters and alert.status.value != filters['status']:
                    matches = False
                if matches:
                    filtered_alerts.append(alert)
            return filtered_alerts
        return alerts
    
    def get_user_alerts(self, user_id: str) -> List[Alert]:
        return self.alert_manager.get_alerts_for_user(user_id)
    
    def snooze_alert(self, user_id: str, alert_id: str):
        state = self.state_manager.get_state(user_id, alert_id)
        state.snooze_until_tomorrow()
        self.state_manager.update_state(state)
    
    def mark_alert_read(self, user_id: str, alert_id: str):
        state = self.state_manager.get_state(user_id, alert_id)
        state.mark_read()
        self.state_manager.update_state(state)
    
    def process_reminders(self):
        self.scheduler.process_reminders()
    
    def get_analytics(self) -> AlertAnalytics:
        return self.analytics.get_system_analytics()

# ===== FLASK WEB SERVER =====
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)

app = Flask(__name__)
app.json_encoder = DateTimeEncoder
system = AlertingSystem()

@app.route('/admin/alerts', methods=['POST'])
def create_alert():
    try:
        data = request.json
        required_fields = ['title', 'message', 'severity', 'created_by', 'visibility_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        severity = Severity(data['severity'])
        
        alert = system.create_alert(
            title=data['title'],
            message=data['message'],
            severity=severity,
            created_by=data['created_by'],
            visibility_type=data['visibility_type'],
            target_ids=set(data.get('target_ids', [])),
            start_time=datetime.fromisoformat(data.get('start_time', datetime.now().isoformat())),
            expiry_time=datetime.fromisoformat(data['expiry_time']) if data.get('expiry_time') else None,
            reminder_frequency=timedelta(hours=data.get('reminder_frequency_hours', 2))
        )
        
        return jsonify({
            'id': alert.id,
            'title': alert.title,
            'message': alert.message,
            'severity': alert.severity.value,
            'status': alert.status.value,
            'created_at': alert.start_time
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/admin/alerts', methods=['GET'])
def list_alerts():
    try:
        filters = {}
        if request.args.get('severity'):
            filters['severity'] = Severity(request.args.get('severity'))
        if request.args.get('status'):
            filters['status'] = request.args.get('status')
        
        alerts = system.list_alerts(filters)
        
        return jsonify([{
            'id': alert.id,
            'title': alert.title,
            'message': alert.message,
            'severity': alert.severity.value,
            'status': alert.status.value,
            'start_time': alert.start_time,
            'expiry_time': alert.expiry_time,
            'created_by': alert.created_by,
            'reminders_enabled': alert.reminders_enabled
        } for alert in alerts])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/admin/alerts/<alert_id>', methods=['PUT'])
def update_alert(alert_id):
    try:
        data = request.json
        updates = {}
        
        if 'title' in data:
            updates['title'] = data['title']
        if 'message' in data:
            updates['message'] = data['message']
        if 'severity' in data:
            updates['severity'] = Severity(data['severity'])
        if 'status' in data:
            updates['status'] = AlertStatus(data['status'])
        if 'reminders_enabled' in data:
            updates['reminders_enabled'] = data['reminders_enabled']
        if 'expiry_time' in data:
            updates['expiry_time'] = datetime.fromisoformat(data['expiry_time'])
        
        alert = system.alert_manager.update_alert(alert_id, **updates)
        
        if alert:
            return jsonify({
                'id': alert.id,
                'title': alert.title,
                'status': alert.status.value,
                'updated': True
            })
        else:
            return jsonify({'error': 'Alert not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/admin/alerts/<alert_id>/archive', methods=['POST'])
def archive_alert(alert_id):
    try:
        success = system.alert_manager.archive_alert(alert_id)
        if success:
            return jsonify({'message': 'Alert archived successfully'})
        else:
            return jsonify({'error': 'Alert not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/users/<user_id>/alerts', methods=['GET'])
def get_user_alerts(user_id):
    try:
        alerts = system.get_user_alerts(user_id)
        
        alert_list = []
        for alert in alerts:
            state = system.state_manager.get_state(user_id, alert.id)
            alert_list.append({
                'id': alert.id,
                'title': alert.title,
                'message': alert.message,
                'severity': alert.severity.value,
                'user_status': state.status.value,
                'snoozed_until': state.snoozed_until,
                'read_at': state.read_at,
                'created_at': alert.start_time
            })
        
        return jsonify(alert_list)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/users/<user_id>/alerts/<alert_id>/read', methods=['POST'])
def mark_alert_read(user_id, alert_id):
    try:
        system.mark_alert_read(user_id, alert_id)
        return jsonify({'message': 'Alert marked as read'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/users/<user_id>/alerts/<alert_id>/snooze', methods=['POST'])
def snooze_alert(user_id, alert_id):
    try:
        system.snooze_alert(user_id, alert_id)
        return jsonify({'message': 'Alert snoozed until tomorrow'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/analytics', methods=['GET'])
def get_analytics():
    try:
        analytics = system.get_analytics()
        
        return jsonify({
            'total_alerts': analytics.total_alerts,
            'active_alerts': analytics.active_alerts,
            'expired_alerts': analytics.expired_alerts,
            'alerts_by_severity': {
                severity.value: count 
                for severity, count in analytics.alerts_by_severity.items()
            },
            'delivery_stats': analytics.delivery_stats
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/system/process-reminders', methods=['POST'])
def process_reminders():
    try:
        system.process_reminders()
        return jsonify({'message': 'Reminders processed successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now()})

if __name__ == '__main__':
    print("Starting Alerting System Server on http://localhost:5000")
    print("Available endpoints:")
    print("  POST   /admin/alerts")
    print("  GET    /admin/alerts")
    print("  PUT    /admin/alerts/<id>")
    print("  POST   /admin/alerts/<id>/archive")
    print("  GET    /users/<id>/alerts")
    print("  POST   /users/<id>/alerts/<id>/read")
    print("  POST   /users/<id>/alerts/<id>/snooze")
    print("  GET    /analytics")
    print("  POST   /system/process-reminders")
    print("  GET    /health")
    app.run(debug=True, host='0.0.0.0', port=5000)
