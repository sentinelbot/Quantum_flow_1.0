# compliance/reporting.py
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ComplianceReporter:
    """
    Comprehensive Regulatory Compliance Reporting System

    Provides advanced reporting capabilities for Anti-Money Laundering (AML), 
    Know Your Customer (KYC), and transaction monitoring compliance.

    The system generates detailed reports to support regulatory oversight 
    and internal risk management processes.
    """

    def __init__(
        self, 
        user_repository=None, 
        trade_repository=None, 
        transaction_repository=None, 
        notification_manager=None, 
        config=None
    ):
        """
        Initialize Compliance Reporting System with configurable dependencies.

        Args:
            user_repository (UserRepository): Repository for user data management
            trade_repository (TradeRepository): Repository for trade data management
            transaction_repository (TransactionRepository): Repository for transaction tracking
            notification_manager (NotificationManager): System for sending notifications
            config (dict, optional): Configuration settings for compliance reporting
        """
        self.user_repo = user_repository
        self.trade_repo = trade_repository
        self.transaction_repo = transaction_repository
        self.notification_manager = notification_manager
        self.config = config or {}

        logger.info("Compliance Reporting System initialized successfully")

    def generate_aml_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Generate Anti-Money Laundering (AML) Compliance Report

        Comprehensive analysis of transactions, user activities, and potential 
        money laundering risks within the specified time period.

        Args:
            start_date (datetime): Beginning of reporting period
            end_date (datetime): End of reporting period

        Returns:
            Dict[str, Any]: Detailed AML compliance report
        """
        try:
            # Validate repository availability
            if not self._validate_repositories():
                return {"error": "Repositories not fully configured"}

            # Retrieve transactions in specified date range
            transactions = self.transaction_repo.get_transactions_in_range(start_date, end_date)

            # User and transaction analysis
            total_users = self.user_repo.count_users()
            verified_users = len(self.user_repo.get_users_by_kyc_status('approved'))
            high_risk_users = len(self.user_repo.get_users_by_aml_risk("high"))

            # Transaction categorization
            deposits = [t for t in transactions if t.transaction_type == "deposit"]
            withdrawals = [t for t in transactions if t.transaction_type == "withdrawal"]
            
            large_deposits = [d for d in deposits if d.amount >= 10000]
            large_withdrawals = [w for w in withdrawals if w.amount >= 10000]

            # Compile comprehensive report
            report = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "user_statistics": {
                    "total_users": total_users,
                    "verified_users": verified_users,
                    "verification_rate": (verified_users / total_users) if total_users > 0 else 0,
                    "high_risk_users": high_risk_users,
                    "high_risk_rate": (high_risk_users / total_users) if total_users > 0 else 0
                },
                "transaction_statistics": {
                    "total_transactions": len(transactions),
                    "deposits": {
                        "count": len(deposits),
                        "total_amount": sum(d.amount for d in deposits),
                        "large_deposits": len(large_deposits),
                        "large_deposits_amount": sum(d.amount for d in large_deposits)
                    },
                    "withdrawals": {
                        "count": len(withdrawals),
                        "total_amount": sum(w.amount for w in withdrawals),
                        "large_withdrawals": len(large_withdrawals),
                        "large_withdrawals_amount": sum(w.amount for w in large_withdrawals)
                    }
                },
                "suspicious_activity": {
                    "flagged_transactions": self.transaction_repo.get_flagged_transactions_count(start_date, end_date),
                    "flagged_users": self.user_repo.get_flagged_users_count()
                },
                "generated_at": datetime.now().isoformat()
            }

            # Optional notification of report generation
            self._notify_report_generation(report)

            return report

        except Exception as e:
            logger.error(f"Error generating AML report: {str(e)}")
            return {"error": str(e)}

    def generate_kyc_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Generate Know Your Customer (KYC) Compliance Report

        Detailed analysis of user registration, KYC submission, and verification 
        processes within the specified time period.

        Args:
            start_date (datetime): Beginning of reporting period
            end_date (datetime): End of reporting period

        Returns:
            Dict[str, Any]: Comprehensive KYC compliance report
        """
        try:
            # Validate repository availability
            if not self.user_repo:
                return {"error": "User repository not configured"}

            # Retrieve users registered in date range
            all_users = self.user_repo.get_all_users()
            users_in_range = [
                u for u in all_users 
                if u.created_at and start_date <= u.created_at <= end_date
            ]

            # KYC statistics
            submitted_kyc = [u for u in users_in_range if u.kyc_submitted_at]
            verified_kyc = [u for u in users_in_range if u.kyc_verified]
            rejected_kyc = [
                u for u in users_in_range 
                if u.kyc_submitted_at and not u.kyc_verified and u.kyc_status == "rejected"
            ]
            pending_kyc = [
                u for u in users_in_range 
                if u.kyc_submitted_at and not u.kyc_verified and u.kyc_status != "rejected"
            ]

            # Compile report
            report = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "registration_statistics": {
                    "new_users": len(users_in_range),
                    "kyc_submitted": len(submitted_kyc),
                    "submission_rate": (len(submitted_kyc) / len(users_in_range)) if users_in_range else 0
                },
                "verification_statistics": {
                    "verified_users": len(verified_kyc),
                    "verification_rate": (len(verified_kyc) / len(submitted_kyc)) if submitted_kyc else 0,
                    "rejected_users": len(rejected_kyc),
                    "rejection_rate": (len(rejected_kyc) / len(submitted_kyc)) if submitted_kyc else 0,
                    "pending_users": len(pending_kyc)
                },
                "verification_timeline": {
                    "average_time_hours": self._calculate_average_verification_time(verified_kyc)
                },
                "generated_at": datetime.now().isoformat()
            }

            return report

        except Exception as e:
            logger.error(f"Error generating KYC report: {str(e)}")
            return {"error": str(e)}

    def generate_regulatory_report(self) -> Dict[str, Any]:
        """
        Generate Comprehensive Monthly Regulatory Compliance Report

        Consolidates AML, KYC, and other compliance-related insights 
        for a holistic view of regulatory compliance.

        Returns:
            Dict[str, Any]: Comprehensive monthly regulatory report
        """
        try:
            # Define date range (previous month)
            end_date = datetime.now()
            start_date = datetime(end_date.year, end_date.month, 1) - timedelta(days=1)
            start_date = datetime(start_date.year, start_date.month, 1)

            # Generate individual reports
            aml_report = self.generate_aml_report(start_date, end_date)
            kyc_report = self.generate_kyc_report(start_date, end_date)

            # Build combined report
            report = {
                "report_type": "monthly_regulatory_report",
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "aml_report": aml_report,
                "kyc_report": kyc_report,
                "generated_at": datetime.now().isoformat()
            }

            return report

        except Exception as e:
            logger.error(f"Error generating regulatory report: {str(e)}")
            return {"error": str(e)}

    def _validate_repositories(self) -> bool:
        """
        Validate the availability of required repositories.

        Returns:
            bool: Indicates whether all necessary repositories are configured
        """
        required_repos = [
            self.user_repo, 
            self.transaction_repo
        ]
        return all(required_repos)

    def _calculate_average_verification_time(self, verified_users: List[Any]) -> float:
        """
        Calculate average KYC verification time in hours.

        Args:
            verified_users (List[Any]): List of users who completed KYC verification

        Returns:
            float: Average verification time in hours
        """
        if not verified_users:
            return 0

        total_hours = 0
        count = 0

        for user in verified_users:
            if user.kyc_submitted_at and user.kyc_verified_at:
                time_diff = user.kyc_verified_at - user.kyc_submitted_at
                hours = time_diff.total_seconds() / 3600
                total_hours += hours
                count += 1

        return total_hours / count if count > 0 else 0

    def _notify_report_generation(self, report: Dict[str, Any]):
        """
        Send notification about generated compliance report.

        Args:
            report (Dict[str, Any]): Generated compliance report
        """
        if self.notification_manager:
            message = (
                f"Compliance Report Generated\n"
                f"Total Users: {report['user_statistics']['total_users']}\n"
                f"High-Risk Users: {report['user_statistics']['high_risk_users']}\n"
                f"Total Transactions: {report['transaction_statistics']['total_transactions']}"
            )
            self.notification_manager.send_compliance_report_alert(message)

# Maintain backward compatibility
ComplianceReporting = ComplianceReporter