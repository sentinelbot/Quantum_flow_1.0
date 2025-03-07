# reporting/report_generator.py
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import os
import io

class ReportGenerator:
    """Generates trading reports for users"""
    
    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger(__name__)
        
    def generate_performance_report(self, user_id, days=30, format='csv'):
        """Generate a performance report for a user"""
        try:
            # Get user information
            from database.repository.user_repository import UserRepository
            user_repo = UserRepository(self.db)
            user = user_repo.get_user_by_id(user_id)
            
            if not user:
                self.logger.error(f"User not found: {user_id}")
                return None
                
            # Get profit statistics
            from profit.stats_service import StatsService
            stats_service = StatsService(self.db)
            stats = stats_service.get_user_profit_statistics(user_id, days)
            
            # Get daily profit history
            daily_profits = stats_service.get_daily_profit_history(user_id, days)
            
            # Get strategy performance
            strategy_stats = stats_service.get_strategy_performance(user_id, days=days)
            
            # Create report data
            report_data = self._create_report_data(user, stats, daily_profits, strategy_stats, days)
            
            # Generate the report in the requested format
            if format.lower() == 'csv':
                return self._generate_csv_report(report_data)
            elif format.lower() == 'pdf':
                return self._generate_pdf_report(report_data)
            else:
                self.logger.error(f"Unsupported report format: {format}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating performance report: {e}")
            return None
            
    def _create_report_data(self, user, stats, daily_profits, strategy_stats, days):
        """Create structured report data"""
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Create report data structure
        report_data = {
            'report_info': {
                'user_id': user.id,
                'email': user.email,
                'report_date': end_date.strftime('%Y-%m-%d'),
                'period_start': start_date.strftime('%Y-%m-%d'),
                'period_end': end_date.strftime('%Y-%m-%d'),
                'days': days
            },
            'performance_summary': stats,
            'daily_profits': daily_profits,
            'strategy_performance': strategy_stats
        }
        
        return report_data
        
    def _generate_csv_report(self, report_data):
        """Generate a CSV report"""
        try:
            # Create a buffer for the CSV data
            output = io.StringIO()
            
            # Write report header
            output.write(f"Performance Report for User: {report_data['report_info']['email']}\n")
            output.write(f"Period: {report_data['report_info']['period_start']} to {report_data['report_info']['period_end']}\n")
            output.write(f"Generated on: {report_data['report_info']['report_date']}\n\n")
            
            # Write performance summary
            output.write("Performance Summary\n")
            output.write("-------------------\n")
            
            summary = report_data['performance_summary']
            for key, value in summary.items():
                formatted_key = key.replace('_', ' ').title()
                formatted_value = f"{value:.2f}" if isinstance(value, (float, int)) else str(value)
                output.write(f"{formatted_key}: {formatted_value}\n")
                
            output.write("\n")
            
            # Write strategy performance
            output.write("Strategy Performance\n")
            output.write("--------------------\n")
            
            if report_data['strategy_performance']:
                strategy_df = pd.DataFrame(report_data['strategy_performance'])
                output.write(strategy_df.to_csv(index=False))
            else:
                output.write("No strategy data available.\n")
                
            output.write("\n")
            
            # Write daily profits
            output.write("Daily Profits\n")
            output.write("-------------\n")
            
            if report_data['daily_profits']:
                profits_df = pd.DataFrame(report_data['daily_profits'])
                output.write(profits_df.to_csv(index=False))
            else:
                output.write("No daily profit data available.\n")
                
            # Get the CSV content and reset the buffer
            csv_content = output.getvalue()
            output.close()
            
            return csv_content
            
        except Exception as e:
            self.logger.error(f"Error generating CSV report: {e}")
            return None
            
    def _generate_pdf_report(self, report_data):
        """Generate a PDF report"""
        try:
            # This is a placeholder for actual PDF generation
            # For a production system, you would use a library like ReportLab or WeasyPrint
            
            self.logger.warning("PDF report generation not fully implemented")
            
            # Return the CSV report as a fallback
            return self._generate_csv_report(report_data)
            
        except Exception as e:
            self.logger.error(f"Error generating PDF report: {e}")
            return None