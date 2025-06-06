from simple_salesforce import Salesforce
import pandas as pd
import pyodbc 
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import configparser
import os
import sys
import logging
import gc

# Set up comprehensive logging with file and console output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('dedupe_iq.log'),
        logging.StreamHandler()
    ]
)

def get_config_path():
    """
    Dynamically determine configuration file path for both development and production deployment
    Supports both standard Python execution and compiled executable deployment
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        bundle_dir = os.path.dirname(sys.executable)
    else:
        # Running as Python script
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(bundle_dir, 'config.ini')
    logging.info(f"Config path: {config_path}")
    logging.info(f"Config file exists: {os.path.exists(config_path)}")
    return config_path

def export_dataframe_to_csv(df, file_path):
    """
    Safely export DataFrame to CSV with directory creation and comprehensive logging
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    logging.info(f"Exporting data to: {file_path}")
    df.to_csv(file_path, index=False)
    logging.info(f"Export complete: {len(df)} rows written")

def process_account_duplicates(df):
    """
    Advanced duplicate detection algorithm that identifies and processes duplicate records
    based on account and phone number combinations.
    
    Business Logic:
    - Groups records by Account ID and Phone Number
    - For duplicate groups, keeps the most recent record (by CreatedDate)
    - Returns older duplicate records for removal
    - Maintains data integrity while eliminating redundant outbound calling
    
    Args:
        df (DataFrame): Input DataFrame with account and phone data
        
    Returns:
        DataFrame: Records identified for removal (older duplicates)
    """
    logging.info("Processing account duplicates")
    df['CreatedDate'] = pd.to_datetime(df['CreatedDate']).dt.date
    grouped = df.groupby(['Account__c', 'Phone_Text__c'])
    
    def process_group(group):
        """
        Process individual duplicate groups - keep newest, return older records for removal
        """
        if len(group) > 1:
            # Sort by date descending, return all but the most recent
            sorted_group = group.sort_values('CreatedDate', ascending=False)
            return sorted_group.iloc[1:]  # Return older records for removal
        return pd.DataFrame()  # No duplicates found
    
    result = grouped.apply(process_group).reset_index(drop=True)
    logging.info(f"Found {len(result)} duplicate records")
    return result[['Account__c', 'Id', 'Phone_Text__c', 'CreatedDate']]

def clean_phone_number(phone):
    """
    Utility function to normalize phone numbers by extracting only digits
    """
    return ''.join(filter(str.isdigit, str(phone)))

def create_email_body(step_statuses):
    """
    Generate formatted email body with job execution status and metadata
    """
    header = """#Source: PRODUCTION_SERVER
#JOB Name: DeDupe IQ
#Schedule: Daily @ 6:30 AM
#Description: Automated duplicate record identification and removal process"""
    
    if isinstance(step_statuses, dict):
        formatted_statuses = "\n".join([f"{step}: {status}" for step, status in step_statuses.items()])
    elif isinstance(step_statuses, str):
        status_lines = step_statuses.split('\n')
        formatted_statuses = "\n".join([line.strip() for line in status_lines])
    else:
        formatted_statuses = "Error: Invalid step_statuses format"
    
    return f"{header}\n\nJob Status:\n{formatted_statuses}"

def send_email(subject, step_statuses, config):
    """
    Send automated status email with retry logic and comprehensive error handling
    """
    try:
        logging.info("Starting email send process")
        message = MIMEMultipart()
        message["From"] = config['Email']['sender_email']
        
        recipients = [email.strip() for email in config['Email']['recipients'].split(',')]
        message["To"] = ", ".join(recipients)
        message["Subject"] = subject
        
        body = create_email_body(step_statuses)
        message.attach(MIMEText(body, "plain"))

        # Use corporate SMTP server with TLS encryption
        with smtplib.SMTP(config['Email']['smtp_server'], int(config['Email']['smtp_port'])) as server:
            server.starttls()
            server.login(config['Email']['sender_email'], config['Email']['sender_password'])
            server.send_message(message)
            logging.info("Email sent successfully")
            
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")
        raise

def main():
    """
    Main execution flow with comprehensive error handling and status tracking
    Implements enterprise-grade logging and notification framework
    """
    step_statuses = {}
    email_sent = False
    
    try:
        # Read configuration from secure config file
        config = configparser.ConfigParser()
        config.read(get_config_path())
        
        # Validate required configuration sections and values
        required_configs = {
            'Paths': ['dedupe_output_path'],
            'Salesforce': ['username', 'password', 'security_token'],
            'Email': ['sender_email', 'sender_password', 'recipients', 'smtp_server', 'smtp_port']
        }
        
        for section, keys in required_configs.items():
            if section not in config:
                raise KeyError(f"Missing required config section: {section}")
            for key in keys:
                if key not in config[section]:
                    raise KeyError(f"Missing required config value: {section}.{key}")
        
        # Establish Salesforce connection with authentication
        logging.info("Connecting to Salesforce")
        sf = Salesforce(
            username=config['Salesforce']['username'],
            password=config['Salesforce']['password'],
            security_token=config['Salesforce']['security_token']
        )
        step_statuses["Salesforce Connection"] = "Success\n"
        
        # Execute comprehensive Salesforce query for duplicate analysis
        logging.info("Fetching phone number data from Salesforce")
        sf_query = """
        SELECT Id, account__c, phone_text__c, CreatedDate
        FROM researched_phone_number__c
        WHERE verified_number_as__c = ''
        AND account__r.inactive__c = false
        AND account__r.minor__c = ''
        AND phone_text__c != ''
        AND phone_text__c != '9999999999'
        AND account__r.initial_marketing_campaign__c != 'EXCLUDED_CAMPAIGN_ID'
        AND account__r.owner.user_is_ae__c = 0
        AND account__r.owner.NAME != 'LEGAL_TEAM'
        AND account__r.of_active_deals__c = 0
        AND record_status__c NOT IN('Post deal 30', 'No More Payments',
                                  'Legal Hold – Impasse', 'DNC Requested')
        """
        
        # Process Salesforce query results into DataFrame
        sf_data = sf.query_all(sf_query)
        rf = pd.DataFrame([dict(row) for row in sf_data["records"]])
        rf = rf.drop('attributes', axis=1)  # Remove Salesforce metadata
        step_statuses["Get Phone Number Data"] = "Success\n"
        
        # Execute advanced duplicate detection algorithm
        duplicates = process_account_duplicates(rf)
        step_statuses["Process Duplicate Analysis"] = "Success\n"
        
        # Export results to configured output path
        output_path = config['Paths']['dedupe_output_path']
        export_dataframe_to_csv(duplicates, output_path)
        step_statuses["Export Duplicate Data"] = "Success\n"
        
        # Memory cleanup for large dataset processing
        del rf
        gc.collect()
        
    except Exception as e:
        logging.error(f"Error in main execution: {str(e)}")
        step_statuses["Script Execution"] = f"Failed: {str(e)}\n"
    
    finally:
        # Implement retry logic for critical email notifications
        max_retries = 3
        retry_count = 0
        
        while not email_sent and retry_count < max_retries:
            try:
                send_email("DeDupe IQ Job Status", step_statuses, config)
                email_sent = True
                logging.info("Status email sent successfully")
            except Exception as email_error:
                retry_count += 1
                logging.error(f"Failed to send email (attempt {retry_count}): {str(email_error)}")
                if retry_count < max_retries:
                    logging.info("Retrying email send...")
                else:
                    logging.error("Maximum email retry attempts reached")
        
        if not email_sent:
            logging.critical("Failed to send status email after all retry attempts")
            sys.exit(1)  # Exit with error status if email couldn't be sent

if __name__ == "__main__":
    main()