import psutil
import time
import logging
from datetime import datetime
from typing import Dict, List

from database.db import get_db_connection
from notification.notification_manager import NotificationManager

logger = logging.getLogger(__name__)

class SystemMonitoring:
    def __init__(self, notification_manager=None):
        self.notification_manager = notification_manager or NotificationManager()
        self.health_status = "Green"
        self.error_counts = {
            "critical": 0,
            "major": 0,
            "minor": 0
        }
        
    def check_system_resources(self) -> Dict:
        """Check CPU, memory, and disk usage"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        disk_percent = psutil.disk_usage('/').percent
        
        status = {
            "cpu": {"usage": cpu_percent, "status": "Green"},
            "memory": {"usage": memory_percent, "status": "Green"},
            "disk": {"usage": disk_percent, "status": "Green"}
        }
        
        # Set status based on thresholds
        if cpu_percent > 90:
            status["cpu"]["status"] = "Red"
        elif cpu_percent > 75:
            status["cpu"]["status"] = "Yellow"
            
        if memory_percent > 90:
            status["memory"]["status"] = "Red"
        elif memory_percent > 75:
            status["memory"]["status"] = "Yellow"
            
        if disk_percent > 90:
            status["disk"]["status"] = "Red"
        elif disk_percent > 75:
            status["disk"]["status"] = "Yellow"
            
        return status
        
    def check_database_health(self) -> Dict:
        """Check database connection and performance"""
        try:
            start_time = time.time()
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            query_time = time.time() - start_time
            
            status = {
                "connected": True,
                "response_time": query_time,
                "status": "Green"
            }
            
            if query_time > 1.0:
                status["status"] = "Red"
            elif query_time > 0.5:
                status["status"] = "Yellow"
                
            cursor.close()
            conn.close()
            return status
            
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}")
            return {
                "connected": False,
                "response_time": None,
                "status": "Red",
                "error": str(e)
            }
    
    def get_overall_system_health(self) -> str:
        """Get overall system health status"""
        resources = self.check_system_resources()
        db_health = self.check_database_health()
        
        # If any system is red, overall status is red
        if (resources["cpu"]["status"] == "Red" or
            resources["memory"]["status"] == "Red" or
            resources["disk"]["status"] == "Red" or
            db_health["status"] == "Red"):
            return "Red"
            
        # If any system is yellow, overall status is yellow
        if (resources["cpu"]["status"] == "Yellow" or
            resources["memory"]["status"] == "Yellow" or
            resources["disk"]["status"] == "Yellow" or
            db_health["status"] == "Yellow"):
            return "Yellow"
            
        return "Green"
    
    def run_monitoring_cycle(self):
        """Run a complete monitoring cycle and alert if needed"""
        previous_status = self.health_status
        self.health_status = self.get_overall_system_health()
        
        # Alert on status degradation
        if self.health_status == "Red" and previous_status != "Red":
            self.notification_manager.send_admin_alert(
                "CRITICAL: System health degraded to RED",
                self.generate_status_report()
            )
        elif self.health_status == "Yellow" and previous_status == "Green":
            self.notification_manager.send_admin_alert(
                "WARNING: System health degraded to YELLOW",
                self.generate_status_report()
            )
            
        # Log current status
        logger.info(f"System health status: {self.health_status}")
        
    def generate_status_report(self) -> str:
        """Generate detailed system status report"""
        resources = self.check_system_resources()
        db_health = self.check_database_health()
        
        report = f"System Status Report - {datetime.now()}\n\n"
        report += f"Overall Status: {self.health_status}\n\n"
        
        report += "Resource Usage:\n"
        report += f"  CPU: {resources['cpu']['usage']}% ({resources['cpu']['status']})\n"
        report += f"  Memory: {resources['memory']['usage']}% ({resources['memory']['status']})\n"
        report += f"  Disk: {resources['disk']['usage']}% ({resources['disk']['status']})\n\n"
        
        report += "Database Health:\n"
        report += f"  Connected: {db_health['connected']}\n"
        if db_health['connected']:
            report += f"  Response Time: {db_health['response_time']:.3f}s ({db_health['status']})\n"
        else:
            report += f"  Error: {db_health.get('error', 'Unknown error')}\n"
            
        return report