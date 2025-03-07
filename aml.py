# compliance/aml.py
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AMLChecker:
    """
    Anti-Money Laundering (AML) Compliance Monitoring System

    Comprehensive risk assessment and transaction monitoring system 
    designed to detect and mitigate potential financial irregularities.
    """

    # Risk level classification
    RISK_LOW = "low"
    RISK_MEDIUM = "medium"
    RISK_HIGH = "high"

    def __init__(
        self, 
        user_repository=None, 
        trade_repository=None, 
        transaction_repository=None, 
        notification_manager=None, 
        config=None
    ):
        """
        Initialize AML Compliance Checker with configurable dependencies.

        Args:
            user_repository (UserRepository): Repository for user data management
            trade_repository (TradeRepository): Repository for trade data management
            transaction_repository (TransactionRepository): Repository for transaction tracking
            notification_manager (NotificationManager): System for sending critical alerts
            config (dict, optional): Configuration settings for AML processing
        """
        # Initialize repositories and dependencies
        self.user_repo = user_repository
        self.trade_repo = trade_repository
        self.transaction_repo = transaction_repository
        self.notification_manager = notification_manager
        
        # Configuration management
        self.config = config or {}
        
        # Define risk assessment thresholds
        self.deposit_threshold = self.config.get('aml.deposit_threshold', 10000)
        self.withdrawal_threshold = self.config.get('aml.withdrawal_threshold', 10000)
        self.rapid_transaction_count = self.config.get('aml.rapid_transaction_count', 5)
        self.rapid_transaction_hours = self.config.get('aml.rapid_transaction_hours', 24)
        
        # AML check history
        self.check_history = {}
        
        logger.info("AML Compliance Checker initialized successfully")
    
    def run_periodic_checks(self):
        """
        Execute scheduled Anti-Money Laundering compliance checks across all users.
        
        Performs systematic analysis of transaction patterns, deposit/withdrawal 
        behaviors, and trading activities to identify potential compliance issues.
        
        Returns:
            bool: True if checks completed successfully
        """
        try:
            logger.info("Running scheduled AML compliance checks")
            
            # Get all users to check
            users = self._get_users_to_check()
            
            if not users:
                logger.info("No users requiring AML checks at this time")
                return True
                
            check_results = {}
            alert_count = 0
            
            for user in users:
                try:
                    # Run risk assessment for user
                    assessment = self.assess_user_risk(user.id)
                    
                    # Store assessment results
                    check_results[user.id] = assessment
                    
                    # Generate alerts for high-risk users
                    if assessment.get('risk_level') == self.RISK_HIGH:
                        alert_count += 1
                        
                except Exception as e:
                    logger.error(f"Error performing AML checks for user {user.id}: {str(e)}")
            
            # Record compliance check execution
            self._record_compliance_check(check_results)
            
            logger.info(f"AML compliance checks completed: checked {len(users)} users, generated {alert_count} alerts")
            return True
            
        except Exception as e:
            logger.error(f"AML compliance checks failed: {str(e)}")
            return False

    def assess_user_risk(self, user_id: int) -> Dict[str, Any]:
        """
        Conduct comprehensive AML risk assessment for a specific user.

        Evaluates user's transaction history, KYC status, and potential 
        money laundering indicators.

        Args:
            user_id (int): Unique identifier for the user to assess

        Returns:
            Dict[str, Any]: Detailed risk assessment with actionable insights
        """
        try:
            # Validate system configuration
            if not self._validate_repositories():
                return {
                    "status": "error",
                    "message": "Incomplete system configuration"
                }

            # Retrieve user information
            user = self.user_repo.get_user_by_id(user_id)
            if not user:
                return {
                    "status": "error", 
                    "message": f"User {user_id} not found"
                }

            # Preliminary KYC verification check
            if not self._check_kyc_status(user):
                return {
                    "risk_level": self.RISK_HIGH,
                    "reason": "KYC verification incomplete",
                    "trading_allowed": False
                }

            # Analyze transaction patterns
            risk_factors = self._analyze_transaction_patterns(user_id)

            # Determine risk level and trading permissions
            risk_level, trading_allowed, reason = self._calculate_risk_level(risk_factors)

            # Update user risk profile if necessary
            self._handle_high_risk_user(user_id, risk_level, reason)

            # Generate comprehensive risk assessment report
            return {
                "user_id": user_id,
                "risk_level": risk_level,
                "reason": reason,
                "trading_allowed": trading_allowed,
                "risk_factors": risk_factors,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Risk assessment failed for user {user_id}: {str(e)}")
            return {
                "status": "error",
                "message": "Unexpected system error during risk assessment"
            }
    
    def _get_users_to_check(self):
        """
        Determine which users require AML checks in this cycle.
        
        Returns:
            list: User objects requiring checks
        """
        try:
            # If no user repository, we can't perform checks
            if not self.user_repo:
                logger.warning("User repository not available for AML checks")
                return []
            
            # Get active users with transaction activity
            active_users = self.user_repo.get_active_users()
            
            # Filter users based on last check time
            # In production, you might prioritize based on risk scores or activity levels
            users_to_check = []
            current_time = datetime.now()
            
            for user in active_users:
                user_id = user.id
                
                # Check if user was recently checked
                if user_id in self.check_history:
                    last_check = self.check_history[user_id].get('last_check_time')
                    if last_check:
                        # Skip users checked within the last 24 hours
                        last_check_time = datetime.fromisoformat(last_check)
                        if (current_time - last_check_time) < timedelta(hours=24):
                            continue
                
                users_to_check.append(user)
            
            return users_to_check
            
        except Exception as e:
            logger.error(f"Error determining users for AML checks: {str(e)}")
            return []
    
    def _record_compliance_check(self, results):
        """
        Record that compliance checks were performed.
        
        Args:
            results: Results of checks
        """
        try:
            # Record check execution time
            timestamp = datetime.now().isoformat()
            
            # Update check history for each user
            for user_id, assessment in results.items():
                self.check_history[user_id] = {
                    'last_check_time': timestamp,
                    'last_risk_level': assessment.get('risk_level', self.RISK_LOW),
                    'last_reason': assessment.get('reason', '')
                }
            
            # In a production system, this would be stored in a database
            logger.info(f"Recorded AML compliance check at {timestamp} for {len(results)} users")
            
        except Exception as e:
            logger.error(f"Error recording compliance check: {str(e)}")
    
    def _check_suspicious_trading_patterns(self, user_id):
        """
        Analyze trading activities for suspicious patterns.
        
        Args:
            user_id: User identifier
            
        Returns:
            list: Suspicious patterns identified
        """
        try:
            suspicious_patterns = []
            
            # Skip if trade repository isn't available
            if not self.trade_repo:
                return suspicious_patterns
                
            # Get recent trading activity
            recent_trades = self.trade_repo.get_trades_by_user(
                user_id=user_id,
                start_date=datetime.now() - timedelta(days=30)
            )
            
            if not recent_trades:
                return suspicious_patterns
                
            # Check for wash trading (trading with oneself)
            wash_trading = self._detect_wash_trading(recent_trades)
            if wash_trading:
                suspicious_patterns.append({
                    "pattern": "wash_trading",
                    "count": len(wash_trading),
                    "severity": self.RISK_HIGH
                })
                
            # Check for layering (rapid buys and sells to create artificial volume)
            layering = self._detect_layering(recent_trades)
            if layering:
                suspicious_patterns.append({
                    "pattern": "layering",
                    "count": len(layering),
                    "severity": self.RISK_MEDIUM
                })
                
            # Check for spoofing (placing and quickly canceling large orders)
            spoofing = self._detect_spoofing(recent_trades)
            if spoofing:
                suspicious_patterns.append({
                    "pattern": "spoofing",
                    "count": len(spoofing),
                    "severity": self.RISK_MEDIUM
                })
                
            return suspicious_patterns
            
        except Exception as e:
            logger.error(f"Error checking trading patterns for user {user_id}: {str(e)}")
            return []

    def _validate_repositories(self) -> bool:
        """
        Validate the availability of required repositories.

        Returns:
            bool: Indicates whether all necessary repositories are configured
        """
        # User repository is essential
        if not self.user_repo:
            return False
        
        # Either transaction or trade repository is needed
        if not self.transaction_repo and not self.trade_repo:
            return False
            
        return True

    def _check_kyc_status(self, user) -> bool:
        """
        Verify user's Know Your Customer (KYC) status.

        Args:
            user: User object to verify

        Returns:
            bool: Indicates whether KYC verification is complete
        """
        return getattr(user, 'kyc_verified', False)

    def _analyze_transaction_patterns(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Analyze detailed transaction patterns for potential AML risks.

        Args:
            user_id (int): User identifier to analyze

        Returns:
            List[Dict[str, Any]]: Comprehensive list of identified risk factors
        """
        risk_factors = []

        # Skip detailed analysis if transaction repository isn't available
        if not self.transaction_repo:
            return risk_factors

        # Large deposit analysis
        large_deposits = self._get_large_transactions(
            user_id, 
            "deposit", 
            self.deposit_threshold
        )
        if large_deposits:
            risk_factors.append({
                "factor": "large_deposits",
                "count": len(large_deposits),
                "total_amount": sum(deposit.amount for deposit in large_deposits)
            })

        # Large withdrawal analysis
        large_withdrawals = self._get_large_transactions(
            user_id, 
            "withdrawal", 
            self.withdrawal_threshold
        )
        if large_withdrawals:
            risk_factors.append({
                "factor": "large_withdrawals",
                "count": len(large_withdrawals),
                "total_amount": sum(withdrawal.amount for withdrawal in large_withdrawals)
            })

        # Rapid transaction detection
        rapid_transactions = self._detect_rapid_transactions(user_id)
        if rapid_transactions:
            risk_factors.append({
                "factor": "rapid_transactions",
                "count": len(rapid_transactions),
                "period_hours": self.rapid_transaction_hours
            })
            
        # Check for structuring (multiple transactions just below thresholds)
        structuring = self._detect_structuring(user_id)
        if structuring:
            risk_factors.append({
                "factor": "structuring",
                "count": len(structuring),
                "total_amount": sum(transaction.amount for transaction in structuring)
            })
            
        # Check for suspicious trading patterns
        suspicious_trading = self._check_suspicious_trading_patterns(user_id)
        for pattern in suspicious_trading:
            risk_factors.append({
                "factor": f"suspicious_trading_{pattern['pattern']}",
                "count": pattern['count'],
                "severity": pattern['severity']
            })

        return risk_factors
    
    def _detect_structuring(self, user_id):
        """
        Detect structuring attempts (transactions below reporting thresholds).
        
        Args:
            user_id: User identifier
            
        Returns:
            list: Potential structuring transactions
        """
        try:
            # Set threshold just below reporting limits
            structuring_threshold = self.deposit_threshold * 0.9
            
            # Get recent transactions
            recent_transactions = self.transaction_repo.get_transactions_by_user(
                user_id=user_id,
                start_date=datetime.now() - timedelta(days=14)
            )
            
            structuring_candidates = []
            
            # Look for multiple transactions just below thresholds
            for transaction in recent_transactions:
                if (transaction.amount > structuring_threshold and 
                    transaction.amount < self.deposit_threshold):
                    structuring_candidates.append(transaction)
            
            # Only flag as structuring if there are multiple such transactions
            if len(structuring_candidates) >= 3:
                return structuring_candidates
                
            return []
            
        except Exception as e:
            logger.error(f"Error detecting structuring for user {user_id}: {str(e)}")
            return []
    
    def _detect_wash_trading(self, trades):
        """
        Detect potential wash trading (trading with oneself).
        
        Args:
            trades: List of trades to analyze
            
        Returns:
            list: Potential wash trading instances
        """
        # This is a simplified implementation
        # In a real system, you would need to analyze order book data
        # and check if buy and sell orders match characteristics
        return []
    
    def _detect_layering(self, trades):
        """
        Detect potential layering (rapid buys and sells to create artificial volume).
        
        Args:
            trades: List of trades to analyze
            
        Returns:
            list: Potential layering instances
        """
        # This is a simplified implementation
        # In a real system, you would analyze time-sequenced order placements
        return []
    
    def _detect_spoofing(self, trades):
        """
        Detect potential spoofing (placing and quickly canceling large orders).
        
        Args:
            trades: List of trades to analyze
            
        Returns:
            list: Potential spoofing instances
        """
        # This is a simplified implementation
        # In a real system, you would analyze order placements and cancellations
        return []

    def _get_large_transactions(
        self, 
        user_id: int, 
        transaction_type: str, 
        threshold: float
    ) -> List:
        """
        Retrieve large transactions for a specific user and type.

        Args:
            user_id (int): User identifier
            transaction_type (str): Type of transaction
            threshold (float): Amount threshold for large transactions

        Returns:
            List: Transactions exceeding the specified threshold
        """
        return self.transaction_repo.get_large_transactions(
            user_id=user_id,
            transaction_type=transaction_type,
            threshold=threshold,
            days=30
        )

    def _detect_rapid_transactions(self, user_id: int) -> List:
        """
        Detect rapid succession of transactions.

        Args:
            user_id (int): User identifier

        Returns:
            List: Transactions occurring within a short time frame
        """
        return self.transaction_repo.get_transactions_by_user(
            user_id=user_id,
            start_date=datetime.now() - timedelta(hours=self.rapid_transaction_hours)
        )

    def _calculate_risk_level(
        self, 
        risk_factors: List[Dict[str, Any]]
    ) -> Tuple[str, bool, str]:
        """
        Calculate comprehensive risk level based on identified factors.

        Args:
            risk_factors (List[Dict[str, Any]]): Identified risk indicators

        Returns:
            Tuple containing risk level, trading permission, and reason
        """
        if not risk_factors:
            return self.RISK_LOW, True, "Normal transaction activity"

        # Check for high severity risk factors
        high_severity_factors = [f for f in risk_factors if f.get('severity') == self.RISK_HIGH]
        if high_severity_factors:
            return (
                self.RISK_HIGH,
                False,
                f"Critical risk detected: {high_severity_factors[0].get('factor', 'suspicious activity')}"
            )

        if len(risk_factors) == 1:
            return (
                self.RISK_MEDIUM, 
                True, 
                f"Potential risk detected: {risk_factors[0]['factor']}"
            )

        # Multiple medium-risk factors escalate to high risk
        if len(risk_factors) >= 3:
            return (
                self.RISK_HIGH,
                False,
                "Multiple suspicious transaction patterns detected"
            )

        return (
            self.RISK_MEDIUM,
            True,
            "Multiple unusual transaction patterns detected"
        )

    def _handle_high_risk_user(self, user_id: int, risk_level: str, reason: str):
        """
        Manage high-risk user profiles and trigger necessary actions.

        Args:
            user_id (int): User identifier
            risk_level (str): Calculated risk level
            reason (str): Rationale for risk classification
        """
        if risk_level == self.RISK_HIGH:
            # Update user risk profile
            if self.user_repo:
                self.user_repo.update_user(
                    user_id=user_id,
                    aml_risk_level=risk_level,
                    aml_reason=reason,
                    aml_timestamp=datetime.now()
                )

            # Send critical notification
            if self.notification_manager:
                self.notification_manager.send_critical_alert(
                    f"HIGH AML RISK: User {user_id} - {reason}"
                )
                
                # Send compliance team notification
                self.notification_manager.send_compliance_notification(
                    title="High Risk AML Alert",
                    message=f"User {user_id} has been flagged as high risk: {reason}",
                    user_id=user_id,
                    risk_level=risk_level
                )

# Maintain backward compatibility
AMLMonitor = AMLChecker