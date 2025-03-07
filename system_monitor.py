import logging
import threading
import time
import os
import psutil
import gc
from typing import Dict, List, Optional, Any, Tuple

logger = logging.getLogger(__name__)

class SystemMonitor:
    """
    Comprehensive System Monitoring and Alerting System

    Provides advanced real-time monitoring of system resources, 
    performance tracking, and critical alert management to ensure 
    optimal system health and operational efficiency.
    """

    def __init__(
        self, 
        notification_manager=None, 
        config=None
    ):
        """
        Initialize System Monitor with configurable dependencies.

        Args:
            notification_manager (NotificationManager, optional): System for sending critical alerts
            config (dict, optional): Configuration settings for system monitoring
        """
        # Initialize dependencies
        self.notification_manager = notification_manager
        self.config = config or {}
        self.logger = logger

        # Get thresholds from system config if available
        system_config = self.config.get('system', {})
        memory_config = system_config.get('memory', {}) if isinstance(system_config, dict) else {}
        
        # Monitoring configuration with defaults
        self.thresholds = {
            "cpu_warning": self.config.get('monitoring.cpu_warning', 80.0),
            "cpu_critical": self.config.get('monitoring.cpu_critical', 95.0),
            "memory_warning": memory_config.get('warning_threshold_percentage', 80.0),
            "memory_critical": memory_config.get('critical_threshold_percentage', 95.0),
            "disk_warning": self.config.get('monitoring.disk_warning', 85.0),
            "disk_critical": self.config.get('monitoring.disk_critical', 95.0)
        }

        # Initialize monitoring state
        self.monitoring_thread: Optional[threading.Thread] = None
        self.running = False
        self.last_check_time = 0
        self.consecutive_warnings = {
            "cpu": 0,
            "memory": 0,
            "disk": 0
        }

        # Metrics history
        self.metrics_history = {
            "cpu": [],
            "memory": [],
            "disk": []
        }

        # Last reported alerts to prevent alert spam
        self.last_alerts = {
            "cpu": 0,
            "memory": 0, 
            "disk": 0
        }
        self.alert_cooldown = 300  # 5 minutes between repeated alerts

        # Maximum history size (1 hour at 1-minute intervals)
        self.max_history_size = self.config.get('monitoring.history_size', 60)
        
        # Memory management
        self.memory_check_interval = self.config.get('monitoring.memory_check_interval', 60)
        self.auto_gc_enabled = self.config.get('monitoring.auto_gc_enabled', True)
        
        # Performance tracking
        self.performance_metrics = {
            "component_response_times": {},
            "api_response_times": [],
            "db_query_times": []
        }

        logger.info("System Monitor initialized successfully")

    def start(self):
        """
        Initiate system monitoring process.
        
        Starts a background thread for continuous system resource monitoring,
        enabling real-time performance tracking and alert generation.
        """
        if self.running:
            logger.warning("System monitoring is already active")
            return
            
        logger.info("Initiating system monitoring")
        self.running = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, name="system_monitor_thread")
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
        logger.info("System monitoring successfully started")
    
    def stop(self):
        """
        Terminate the system monitoring process.
        
        Safely stops the monitoring thread and releases system resources,
        ensuring a clean shutdown of the monitoring system.
        """
        if not self.running:
            logger.warning("System monitoring is already stopped")
            return
            
        logger.info("Stopping system monitoring")
        self.running = False
        
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
            if self.monitoring_thread.is_alive():
                logger.warning("System monitoring thread did not terminate gracefully")
            
        logger.info("System monitoring successfully stopped")
    
    def _monitoring_loop(self):
        """
        Continuous monitoring loop for system resources.
        
        Collects metrics at regular intervals, updates historical data,
        and checks for potential performance threshold violations.
        """
        check_count = 0
        
        while self.running:
            try:
                # Collect and process system metrics
                metrics = self._collect_metrics()
                self._update_metrics_history(metrics)
                self._check_thresholds(metrics)
                
                # Perform garbage collection if memory usage is high and auto GC is enabled
                if (self.auto_gc_enabled and 
                    metrics["memory"]["percent"] > self.thresholds["memory_warning"]):
                    self._perform_garbage_collection()
                
                # Perform deeper system checks every 5 iterations (5 minutes)
                check_count += 1
                if check_count >= 5:
                    self._perform_deep_system_check()
                    check_count = 0
                
                # Record last check time
                self.last_check_time = time.time()
                
                # Wait before next monitoring cycle
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in system monitoring loop: {str(e)}")
                time.sleep(60)  # Wait before retry after error
    
    def _collect_metrics(self):
        """
        Collect system metrics
        """
        try:
            # Get process information
            process = psutil.Process(os.getpid())
            process_create_time = process.create_time()
            
            # Collect metrics
            metrics = {
                "cpu": {
                    "percent": psutil.cpu_percent(interval=0.1),
                    "count": psutil.cpu_count()
                },
                "memory": {
                    "percent": psutil.virtual_memory().percent,
                    "available_gb": psutil.virtual_memory().available / (1024 ** 3),
                    "total_gb": psutil.virtual_memory().total / (1024 ** 3)
                },
                "disk": {
                    "percent": psutil.disk_usage('/').percent,
                    "free_gb": psutil.disk_usage('/').free / (1024 ** 3),
                    "total_gb": psutil.disk_usage('/').total / (1024 ** 3)
                },
                "network": {
                    "active_connections": len(psutil.net_connections()),
                    "bytes_sent": psutil.net_io_counters().bytes_sent,
                    "bytes_recv": psutil.net_io_counters().bytes_recv
                },
                "process": {
                    "memory_rss_mb": process.memory_info().rss / (1024 * 1024),
                    "threads_count": process.num_threads(),
                    "open_files": len(process.open_files()),
                    "uptime_seconds": time.time() - process_create_time
                }
            }
            
            return metrics
        except Exception as e:
            self.logger.error(f"Error collecting metrics: {e}")
            return {
                "cpu": {"percent": 0, "count": 0},
                "memory": {"percent": 0, "available_gb": 0, "total_gb": 0},
                "disk": {"percent": 0, "free_gb": 0, "total_gb": 0},
                "network": {"active_connections": 0, "bytes_sent": 0, "bytes_recv": 0},
                "process": {"memory_rss_mb": 0, "threads_count": 0, "open_files": 0, "uptime_seconds": 0}
            }
    
    def _get_memory_metrics(self) -> Dict[str, float]:
        """
        Retrieve detailed memory utilization metrics.
        
        Provides insights into memory usage, total capacity, 
        and available resources.
        
        Returns:
            Dict with memory usage percentages and capacity
        """
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            "percent": memory.percent,
            "total_gb": memory.total / (1024 ** 3),
            "available_gb": memory.available / (1024 ** 3),
            "used_gb": memory.used / (1024 ** 3),
            "swap_percent": swap.percent,
            "swap_total_gb": swap.total / (1024 ** 3),
            "swap_used_gb": swap.used / (1024 ** 3)
        }
    
    def _get_disk_metrics(self) -> Dict[str, Any]:
        """
        Retrieve comprehensive disk utilization metrics.
        
        Offers detailed information about disk space usage 
        and available storage.
        
        Returns:
            Dict with disk usage percentages and capacity
        """
        root_disk = psutil.disk_usage('/')
        
        # Get disk I/O statistics
        disk_io = psutil.disk_io_counters()
        
        return {
            "percent": root_disk.percent,
            "total_gb": root_disk.total / (1024 ** 3),
            "free_gb": root_disk.free / (1024 ** 3),
            "read_count": disk_io.read_count if disk_io else 0,
            "write_count": disk_io.write_count if disk_io else 0,
            "read_bytes": disk_io.read_bytes / (1024 ** 2) if disk_io else 0,  # MB
            "write_bytes": disk_io.write_bytes / (1024 ** 2) if disk_io else 0  # MB
        }
    
    def _get_process_metrics(self) -> Dict[str, Any]:
        """
        Retrieve process-specific resource utilization metrics.
        
        Monitors memory consumption and CPU usage of the current process.
        
        Returns:
            Dict with process memory and CPU usage
        """
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        return {
            "memory_rss_mb": memory_info.rss / (1024 ** 2),  # Resident set size
            "memory_vms_mb": memory_info.vms / (1024 ** 2),  # Virtual memory size
            "cpu_percent": process.cpu_percent(interval=0.1),
            "threads_count": process.num_threads(),
            "open_files": len(process.open_files()),
            "uptime_seconds": time.time() - process.create_time()
        }
    
    def _get_network_metrics(self) -> Dict[str, Any]:
        """
        Retrieve network traffic metrics.
        
        Tracks bytes sent and received to monitor network activity.
        
        Returns:
            Dict with network bytes sent and received
        """
        network = psutil.net_io_counters()
        connections = len(psutil.net_connections())
        
        return {
            "bytes_sent_mb": network.bytes_sent / (1024 ** 2),
            "bytes_recv_mb": network.bytes_recv / (1024 ** 2),
            "packets_sent": network.packets_sent,
            "packets_recv": network.packets_recv,
            "active_connections": connections
        }

    def _get_python_metrics(self) -> Dict[str, Any]:
        """
        Retrieve Python-specific memory and garbage collection metrics.
        
        Provides insights into Python's memory management.
        
        Returns:
            Dict with Python memory metrics
        """
        gc_counts = gc.get_count()
        gc_threshold = gc.get_threshold()
        
        return {
            "gc_counts": gc_counts,
            "gc_threshold": gc_threshold,
            "gc_objects": len(gc.get_objects())
        }

    def get_system_stats(self) -> Dict[str, Any]:
        """
        Generate comprehensive system performance report.
        
        Provides a holistic view of current system metrics, 
        historical performance averages, and overall system status.
        
        Returns:
            Dict with current metrics, historical averages, and system status
        """
        metrics = self._collect_metrics()
        
        return {
            "current": metrics,
            "averages": self._calculate_metric_averages(),
            "status": self._get_system_status(metrics),
            "last_check": self.last_check_time,
            "uptime": self._get_process_metrics()["uptime_seconds"]
        }

    def get_full_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system status with recommendations.
        
        Provides detailed system status along with recommendations
        for addressing any detected issues.
        
        Returns:
            Dict with system status, metrics, and recommendations
        """
        stats = self.get_system_stats()
        recommendations = self._generate_recommendations(stats)
        
        return {
            "status": stats["status"],
            "metrics": stats["current"],
            "averages": stats["averages"],
            "recommendations": recommendations,
            "warnings": self._get_active_warnings(stats["current"]),
            "performance": self._get_performance_metrics()
        }

    def _calculate_metric_averages(self) -> Dict[str, float]:
        """
        Calculate average resource utilization from historical data.
        
        Computes rolling averages for CPU, memory, and disk usage
        to provide a comprehensive performance overview.
        
        Returns:
            Dict with average CPU, memory, and disk usage
        """
        return {
            "cpu": self._safe_average(self.metrics_history["cpu"]),
            "memory": self._safe_average(self.metrics_history["memory"]),
            "disk": self._safe_average(self.metrics_history["disk"])
        }

    def _safe_average(self, values: List[float]) -> float:
        """
        Calculate average safely to prevent division by zero.
        
        Provides a robust method for computing average values
        even with empty or minimal datasets.
        
        Args:
            values: List of numerical values
        
        Returns:
            Average of values or 0 if list is empty
        """
        return sum(values) / max(len(values), 1)

    def _update_metrics_history(self, metrics: Dict[str, Any]) -> None:
        """
        Update historical metrics data.
        
        Maintains a rolling window of resource utilization metrics,
        ensuring consistent performance tracking.
        
        Args:
            metrics: Current system metrics
        """
        # Update metrics history
        self.metrics_history["cpu"].append(metrics["cpu"]["percent"])
        self.metrics_history["memory"].append(metrics["memory"]["percent"])
        self.metrics_history["disk"].append(metrics["disk"]["percent"])
        
        # Trim history to maximum size
        for metric_type in self.metrics_history:
            if len(self.metrics_history[metric_type]) > self.max_history_size:
                self.metrics_history[metric_type] = self.metrics_history[metric_type][-self.max_history_size:]

    def _check_thresholds(self, metrics: Dict[str, Any]) -> None:
        """
        Check and respond to system resource threshold violations.
        
        Monitors CPU, memory, and disk usage, generating alerts
        for warning and critical levels.
        
        Args:
            metrics: Current system metrics
        """
        alerts = []
        current_time = time.time()
        
        # CPU threshold check
        cpu_percent = metrics["cpu"]["percent"]
        if cpu_percent >= self.thresholds["cpu_critical"]:
            if (current_time - self.last_alerts["cpu"]) > self.alert_cooldown:
                alerts.append({
                    "level": "critical",
                    "component": "CPU",
                    "message": f"CPU usage critical: {cpu_percent:.1f}%"
                })
                self.last_alerts["cpu"] = current_time
                self.consecutive_warnings["cpu"] += 1
        elif cpu_percent >= self.thresholds["cpu_warning"]:
            if (current_time - self.last_alerts["cpu"]) > self.alert_cooldown:
                alerts.append({
                    "level": "warning",
                    "component": "CPU",
                    "message": f"CPU usage high: {cpu_percent:.1f}%"
                })
                self.last_alerts["cpu"] = current_time
                self.consecutive_warnings["cpu"] += 1
        else:
            self.consecutive_warnings["cpu"] = 0
        
        # Memory threshold check
        memory_percent = metrics["memory"]["percent"]
        if memory_percent >= self.thresholds["memory_critical"]:
            if (current_time - self.last_alerts["memory"]) > self.alert_cooldown:
                alerts.append({
                    "level": "critical",
                    "component": "Memory",
                    "message": f"Memory usage critical: {memory_percent:.1f}%"
                })
                self.last_alerts["memory"] = current_time
                self.consecutive_warnings["memory"] += 1
                # Trigger garbage collection on critical memory
                if self.auto_gc_enabled:
                    self._perform_garbage_collection()
        elif memory_percent >= self.thresholds["memory_warning"]:
            if (current_time - self.last_alerts["memory"]) > self.alert_cooldown:
                alerts.append({
                    "level": "warning",
                    "component": "Memory",
                    "message": f"Memory usage high: {memory_percent:.1f}%"
                })
                self.last_alerts["memory"] = current_time
                self.consecutive_warnings["memory"] += 1
        else:
            self.consecutive_warnings["memory"] = 0
        
        # Disk threshold check
        disk_percent = metrics["disk"]["percent"]
        if disk_percent >= self.thresholds["disk_critical"]:
            if (current_time - self.last_alerts["disk"]) > self.alert_cooldown:
                alerts.append({
                    "level": "critical",
                    "component": "Disk",
                    "message": f"Disk usage critical: {disk_percent:.1f}%"
                })
                self.last_alerts["disk"] = current_time
                self.consecutive_warnings["disk"] += 1
        elif disk_percent >= self.thresholds["disk_warning"]:
            if (current_time - self.last_alerts["disk"]) > self.alert_cooldown:
                alerts.append({
                    "level": "warning",
                    "component": "Disk",
                    "message": f"Disk usage high: {disk_percent:.1f}%"
                })
                self.last_alerts["disk"] = current_time
                self.consecutive_warnings["disk"] += 1
        else:
            self.consecutive_warnings["disk"] = 0
        
        # Process alerts
        self._process_alerts(alerts)
        
        # Check for persistent issues
        self._check_persistent_issues()

    def _process_alerts(self, alerts: List[Dict[str, str]]) -> None:
        """
        Process and escalate system alerts.
        
        Logs alerts and sends notifications based on severity.
        
        Args:
            alerts: List of detected system alerts
        """
        for alert in alerts:
            # Log alerts based on severity
            if alert["level"] == "critical":
                logger.critical(alert["message"])
            else:
                logger.warning(alert["message"])
            
            # Send admin alerts for critical issues
            if alert["level"] == "critical" and self.notification_manager:
                self.notification_manager.send_admin_alert(
                    subject=f"Critical Alert: {alert['component']}",
                    message=alert["message"]
                )

    def _check_persistent_issues(self) -> None:
        """
        Check for persistent resource utilization issues.
        
        Identifies and escalates resource issues that persist
        across multiple monitoring cycles.
        """
        # Define threshold for consecutive warnings
        consecutive_threshold = 3
        
        # Check each resource for persistent issues
        for resource, count in self.consecutive_warnings.items():
            if count >= consecutive_threshold:
                if self.notification_manager:
                    self.notification_manager.send_admin_alert(
                        subject=f"Persistent {resource.upper()} Issue",
                        message=f"{resource.capitalize()} usage has been high for {count} consecutive checks. Urgent attention required."
                    )
                logger.critical(f"Persistent {resource} issue detected: {count} consecutive warnings")

    def _get_system_status(self, metrics: Dict[str, Any]) -> str:
        """
        Determine system status based on metrics
        """
        try:
            status = "healthy"
            
            # CPU check (>85% = warning, >95% = critical)
            if metrics["cpu"]["percent"] > 95:
                return "critical"
            elif metrics["cpu"]["percent"] > 85:
                status = "warning"
                
            # Memory check (>85% = warning, >95% = critical)
            if metrics["memory"]["percent"] > 95:
                return "critical"
            elif metrics["memory"]["percent"] > 85:
                status = "warning"
                
            # Disk check (>85% = warning, >95% = critical)
            if metrics["disk"]["percent"] > 95:
                return "critical"
            elif metrics["disk"]["percent"] > 85:
                status = "warning"
                
            return status
        except Exception as e:
            self.logger.error(f"Error determining system status: {e}")
            return "unknown"

    def _get_active_warnings(self, metrics: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Get list of active warnings based on current metrics.
        
        Identifies all resources currently exceeding warning thresholds.
        
        Args:
            metrics: Current system metrics
            
        Returns:
            List of warning objects
        """
        warnings = []
        
        if metrics["cpu"]["percent"] >= self.thresholds["cpu_warning"]:
            level = "critical" if metrics["cpu"]["percent"] >= self.thresholds["cpu_critical"] else "warning"
            warnings.append({
                "component": "CPU",
                "level": level,
                "value": f"{metrics['cpu']['percent']:.1f}%",
                "threshold": f"{self.thresholds['cpu_' + level]:.1f}%"
            })
            
        if metrics["memory"]["percent"] >= self.thresholds["memory_warning"]:
            level = "critical" if metrics["memory"]["percent"] >= self.thresholds["memory_critical"] else "warning"
            warnings.append({
                "component": "Memory",
                "level": level,
                "value": f"{metrics['memory']['percent']:.1f}%",
                "threshold": f"{self.thresholds['memory_' + level]:.1f}%"
            })
            
        if metrics["disk"]["percent"] >= self.thresholds["disk_warning"]:
            level = "critical" if metrics["disk"]["percent"] >= self.thresholds["disk_critical"] else "warning"
            warnings.append({
                "component": "Disk",
                "level": level,
                "value": f"{metrics['disk']['percent']:.1f}%",
                "threshold": f"{self.thresholds['disk_' + level]:.1f}%"
            })
            
        return warnings

    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """
        Generate actionable recommendations based on system metrics.
        
        Provides guidance for addressing resource utilization issues.
        
        Args:
            stats: System statistics
            
        Returns:
            List of recommendation strings
        """
        recommendations = []
        metrics = stats["current"]
        
        # CPU recommendations
        if metrics["cpu"]["percent"] >= self.thresholds["cpu_warning"]:
            recommendations.append("Consider limiting the number of concurrent operations or scaling up CPU resources.")
            
        # Memory recommendations
        if metrics["memory"]["percent"] >= self.thresholds["memory_warning"]:
            recommendations.append("Consider optimizing memory usage, increasing swap space, or upgrading memory capacity.")
            if self.auto_gc_enabled:
                recommendations.append("Automatic garbage collection has been triggered to reduce memory usage.")
            
        # Disk recommendations
        if metrics["disk"]["percent"] >= self.thresholds["disk_warning"]:
            recommendations.append("Consider cleaning up temporary files, logs, or increasing disk space.")
            
        # General recommendations if system is unhealthy
        if stats["status"] != "healthy":
            recommendations.append("Run a system diagnostics check using the admin dashboard.")
            recommendations.append("Review recent logs for errors or warnings that might indicate specific issues.")
            
        return recommendations

    def _perform_garbage_collection(self) -> Tuple[int, float]:
        """
        Force garbage collection to free memory.
        
        Triggers Python's garbage collector and tracks performance.
        
        Returns:
            Tuple of (objects collected, time taken)
        """
        logger.info("Performing garbage collection to free memory")
        
        start_time = time.time()
        collected = gc.collect(2)  # Full collection
        duration = time.time() - start_time
        
        logger.info(f"Garbage collection completed in {duration:.2f} seconds: {collected} objects collected")
        
        return collected, duration

    def _perform_deep_system_check(self) -> Dict[str, Any]:
        """
        Perform a deeper system health check.
        
        Runs additional diagnostics to identify potential issues
        that might not be apparent from basic metrics.
        
        Returns:
            Dict with detailed diagnostic results
        """
        results = {
            "timestamp": time.time(),
            "diagnostics": {}
        }
        
        # Check for zombie processes
        try:
            zombie_count = len([p for p in psutil.process_iter() if p.status() == psutil.STATUS_ZOMBIE])
            results["diagnostics"]["zombie_processes"] = zombie_count
            if zombie_count > 5:
                logger.warning(f"High number of zombie processes detected: {zombie_count}")
        except Exception as e:
            logger.error(f"Error checking zombie processes: {str(e)}")
        
        # Check disk I/O
        try:
            disk_io = psutil.disk_io_counters()
            results["diagnostics"]["disk_read_count"] = disk_io.read_count
            results["diagnostics"]["disk_write_count"] = disk_io.write_count
        except Exception as e:
            logger.error(f"Error checking disk I/O: {str(e)}")
        
        # Check for high open file descriptors
        try:
            process = psutil.Process(os.getpid())
            open_files = len(process.open_files())
            results["diagnostics"]["open_files"] = open_files
            if open_files > 1000:
                logger.warning(f"High number of open files detected: {open_files}")
        except Exception as e:
            logger.error(f"Error checking open files: {str(e)}")
            
        return results

    def track_component_response_time(self, component_name: str, response_time: float) -> None:
        """
        Track response times for system components.
        
        Monitors performance of specific components for trend analysis.
        
        Args:
            component_name: Name of the component being tracked
            response_time: Response time in seconds
        """
        if component_name not in self.performance_metrics["component_response_times"]:
            self.performance_metrics["component_response_times"][component_name] = []
            
        metrics = self.performance_metrics["component_response_times"][component_name]
        metrics.append(response_time)
        
        # Keep only the last 100 measurements
        if len(metrics) > 100:
            self.performance_metrics["component_response_times"][component_name] = metrics[-100:]
        
        # Log slow responses
        if response_time > 1.0:  # More than 1 second
            logger.warning(f"Slow response from component {component_name}: {response_time:.2f} seconds")

    def _get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get component performance metrics.
        
        Provides insights into response times of system components.
        
        Returns:
            Dict with component performance metrics
        """
        performance = {}
        
        # Calculate average response times for components
        for component, times in self.performance_metrics["component_response_times"].items():
            if times:
                performance[component] = {
                    "avg_response_time": sum(times) / len(times),
                    "max_response_time": max(times),
                    "min_response_time": min(times)
                }
                
        return performance

    def get_health_status(self) -> str:
        """
        Get system health status
        """
        try:
            metrics = self._collect_metrics()
            status = self._get_system_status(metrics)
            
            status_map = {
                "healthy": "Healthy",
                "warning": "Warning",
                "critical": "Critical"
            }
            
            return status_map.get(status, "Unknown")
        except Exception as e:
            self.logger.error(f"Error getting health status: {e}")
            return "Unknown"

    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get detailed system metrics for dashboard
        """
        try:
            metrics = self._collect_metrics()
            
            return {
                "cpu_usage": f"{metrics['cpu']['percent']:.1f}",
                "memory_usage": f"{metrics['memory']['percent']:.1f}",
                "disk_usage": f"{metrics['disk']['percent']:.1f}",
                "memory_available_gb": f"{metrics['memory']['available_gb']:.2f}",
                "disk_free_gb": f"{metrics['disk']['free_gb']:.2f}",
                "active_connections": metrics["network"]["active_connections"],
                "process_memory_mb": f"{metrics['process']['memory_rss_mb']:.2f}",
                "process_threads": metrics["process"]["threads_count"],
                "open_files": metrics["process"]["open_files"],
                "uptime_hours": f"{metrics['process']['uptime_seconds'] / 3600:.1f}",
                "db_connections": "N/A",  # To be implemented with DB metrics
                "active_users": "N/A",  # To be populated by user repository
                "active_positions": "N/A",  # To be populated by position repository
                "trading_engine_status": "N/A",  # To be populated by trading engine
                "ml_models_status": "N/A",  # To be populated by ML system
                "database_status": "N/A",  # To be populated by database manager
                "notification_status": "N/A",  # To be populated by notification system
                "avg_response_time": "N/A",  # To be calculated from performance metrics
                "last_error": "None"  # To be populated by error tracking
            }
        except Exception as e:
            self.logger.error(f"Error getting system metrics: {e}")
            return {}