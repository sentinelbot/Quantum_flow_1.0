# core/scheduler.py
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Callable, Union, Optional

class Scheduler:
    """
    Advanced Task Scheduling System

    Provides a comprehensive scheduling mechanism for managing 
    periodic jobs with precise execution controls, robust error handling,
    and flexible scheduling options.
    """

    def __init__(
        self, 
        shutdown_event: Optional[threading.Event] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the Scheduler with configurable dependencies.

        Args:
            shutdown_event (threading.Event, optional): Event to signal system shutdown
            config (dict, optional): Configuration settings for scheduling
        """
        # Logging setup
        self.logger = logging.getLogger(__name__)
        
        # Shutdown management
        self.shutdown_event = shutdown_event or threading.Event()
        
        # Job management
        self.tasks: Dict[str, Dict[str, Any]] = {}
        
        # Threading controls
        self.scheduler_thread: Optional[threading.Thread] = None
        self.running = False
        self.lock = threading.Lock()
        
        # Configuration
        self.config = config or {}
        
        self.logger.info("Scheduler initialized successfully")
        
    def start(self) -> bool:
        """
        Initiate the scheduler's background monitoring thread.

        Returns:
            bool: True if scheduler started successfully, False if already running
        """
        if self.running:
            self.logger.warning("Scheduler is already operational")
            return False
            
        self.logger.info("Activating scheduler")
        self.running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        return True
        
    def stop(self) -> bool:
        """
        Gracefully terminate the scheduler.

        Returns:
            bool: True if scheduler stopped successfully, False if already stopped
        """
        if not self.running:
            self.logger.warning("Scheduler is already inactive")
            return False
            
        self.logger.info("Deactivating scheduler")
        self.running = False
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
            
        return True
        
    def _scheduler_loop(self):
        """
        Primary scheduling loop for job execution.

        Continuously monitors and executes scheduled tasks 
        while respecting system shutdown signals.
        """
        while self.running and not self.shutdown_event.is_set():
            try:
                self._check_and_execute_tasks()
                time.sleep(1)  # Check every second
            except Exception as e:
                self.logger.error(f"Critical error in scheduler loop: {e}")
                time.sleep(5)  # Longer sleep on persistent errors
                
    def _check_and_execute_tasks(self):
        """
        Check and execute tasks that are due to run.
        """
        with self.lock:
            now = datetime.now()
            
            for task_id, task in list(self.tasks.items()):
                if self._should_run_task(task, now):
                    # Run the task in a separate thread
                    task_thread = threading.Thread(
                        target=self._execute_task,
                        args=(task_id, task)
                    )
                    task_thread.daemon = True
                    task_thread.start()
                    
                    # Update last run time
                    task['last_run'] = now.timestamp()
                    
    def _should_run_task(self, task: Dict[str, Any], now: datetime) -> bool:
        """
        Determine if a scheduled task should be executed.

        Args:
            task (Dict): Task configuration details
            now (datetime): Current timestamp

        Returns:
            bool: Indicates whether the task should be run
        """
        # Skip paused tasks
        if task.get('is_paused', False):
            return False
        
        # Check task type and execute accordingly
        task_type = task.get('type', 'interval')
        
        if task_type == 'interval':
            # Interval-based task
            interval = task.get('interval', 0)
            last_run = task.get('last_run', 0)
            return (now.timestamp() - last_run) >= interval
        
        elif task_type == 'daily':
            # Daily task at specific time
            return (now.hour == task['hour'] and 
                    now.minute == task['minute'] and 
                    now.second < 1)
        
        elif task_type == 'weekly':
            # Weekly task at specific time and day
            return (now.weekday() == task['day_of_week'] and 
                    now.hour == task['hour'] and 
                    now.minute == task['minute'] and 
                    now.second < 1)
        
        elif task_type == 'monthly':
            # Monthly task at specific time and day
            return (now.day == task['day'] and 
                    now.hour == task['hour'] and 
                    now.minute == task['minute'] and 
                    now.second < 1)
        
        return False
    
    def _execute_task(self, task_id: str, task: Dict[str, Any]):
        """
        Execute a scheduled task with comprehensive error management.

        Args:
            task_id (str): Unique identifier of the task
            task (Dict): Task configuration to execute
        """
        try:
            start_time = time.time()
            
            # Execute task function
            result = task['function'](*task.get('args', ()), **task.get('kwargs', {}))
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Update task metadata
            with self.lock:
                if task_id in self.tasks:
                    self.tasks[task_id]['last_duration'] = duration
            
            self.logger.debug(f"Executed task '{task_id}' in {duration:.2f} seconds")
            return result
        
        except Exception as e:
            self.logger.error(f"Error executing task '{task_id}': {e}")
            return None
        
    def schedule(
        self,
        task_func: Callable,
        interval_seconds: Union[int, float],
        task_id: Optional[str] = None,
        run_at_time: Optional[str] = None,
        is_critical: bool = False,
        *args: Any,
        **kwargs: Any
    ) -> bool:
        """
        Schedule a task with flexible scheduling options.

        Args:
            task_func (Callable): Function to execute
            interval_seconds (Union[int, float]): Interval between executions
            task_id (str, optional): Unique identifier for the task
            run_at_time (str, optional): Specific time to run (format: "HH:MM")
            is_critical (bool, optional): Indicates if task is critical
            *args: Positional arguments for the task function
            **kwargs: Keyword arguments for the task function

        Returns:
            bool: True if task scheduled successfully
        """
        # Generate task ID if not provided
        task_id = task_id or f"task_{len(self.tasks) + 1}"
        
        # Determine task type
        if run_at_time:
            # Parse time for daily/time-based scheduling
            try:
                hour, minute = map(int, run_at_time.split(':'))
                
                # Schedule as daily task
                return self.add_daily_job(
                    task_id, task_func, hour, minute, 
                    is_critical=is_critical, *args, **kwargs
                )
            except (ValueError, IndexError):
                self.logger.error(f"Invalid time format: {run_at_time}")
                return False
        
        # Default to interval-based scheduling
        return self.add_job(
            task_id, task_func, interval_seconds, 
            is_critical=is_critical, *args, **kwargs
        )
    
    def add_job(
        self, 
        task_id: str, 
        task_func: Callable, 
        interval: Union[int, float], 
        is_critical: bool = False,
        *args: Any, 
        **kwargs: Any
    ) -> bool:
        """
        Schedule a recurring task with fixed interval execution.

        Args:
            task_id (str): Unique identifier for the task
            task_func (Callable): Function to be executed
            interval (int/float): Execution interval in seconds
            is_critical (bool, optional): Indicates if task is critical

        Returns:
            bool: True if job added successfully
        """
        with self.lock:
            if task_id in self.tasks:
                self.logger.warning(f"Task '{task_id}' already exists. Overwriting.")
            
            self.tasks[task_id] = {
                'function': task_func,
                'type': 'interval',
                'interval': interval,
                'last_run': 0,  # Immediate first run
                'is_critical': is_critical,
                'is_paused': False,
                'args': args,
                'kwargs': kwargs
            }
        
        self.logger.info(f"Interval job added: {task_id}, {interval}s")
        return True
    
    def remove_task(self, task_id: str) -> bool:
        """
        Remove a scheduled task.

        Args:
            task_id (str): Unique identifier of the task to remove

        Returns:
            bool: True if task removed successfully
        """
        with self.lock:
            if task_id in self.tasks:
                del self.tasks[task_id]
                self.logger.info(f"Task removed: {task_id}")
                return True
            
            self.logger.warning(f"Task not found: {task_id}")
            return False
    
    def pause_task(self, task_id: str) -> bool:
        """
        Pause a scheduled task.

        Args:
            task_id (str): Unique identifier of the task to pause

        Returns:
            bool: True if task paused successfully
        """
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id]['is_paused'] = True
                self.logger.info(f"Paused task: {task_id}")
                return True
            
            self.logger.warning(f"Task not found: {task_id}")
            return False
    
    def resume_task(self, task_id: str) -> bool:
        """
        Resume a paused task.

        Args:
            task_id (str): Unique identifier of the task to resume

        Returns:
            bool: True if task resumed successfully
        """
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id]['is_paused'] = False
                self.logger.info(f"Resumed task: {task_id}")
                return True
            
            self.logger.warning(f"Task not found: {task_id}")
            return False
    
    def pause_non_critical_tasks(self) -> int:
        """
        Pause all non-critical tasks.

        Returns:
            int: Number of tasks paused
        """
        with self.lock:
            paused_count = 0
            
            for task in self.tasks.values():
                if not task['is_critical'] and not task['is_paused']:
                    task['is_paused'] = True
                    paused_count += 1
            
            self.logger.info(f"Paused {paused_count} non-critical tasks")
            return paused_count
    
    def resume_all_tasks(self) -> int:
        """
        Resume all paused tasks.

        Returns:
            int: Number of tasks resumed
        """
        with self.lock:
            resumed_count = 0
            
            for task in self.tasks.values():
                if task['is_paused']:
                    task['is_paused'] = False
                    resumed_count += 1
            
            self.logger.info(f"Resumed {resumed_count} tasks")
            return resumed_count

    # Additional scheduling methods (daily, weekly, monthly jobs) 
    # can be added similarly to the `schedule` and `add_job` methods

# Maintain backward compatibility
TaskScheduler = Scheduler