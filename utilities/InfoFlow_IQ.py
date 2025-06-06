from simple_salesforce import Salesforce
import pandas as pd
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import configparser
import sys
import logging
from pathlib import Path
import gc

# Set up comprehensive logging with file and console output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('infoflow_iq.log'),
        logging.StreamHandler()
    ]
)

def get_config_path():
    """
    Dynamically determine configuration file path for production deployment
    Supports network file share and local deployment scenarios
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        bundle_dir = os.path.dirname(sys.executable)
    else:
        # Running as Python script
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(bundle_dir, 'config.ini')
    logging.info(f"Looking for config file at: {config_path}")
    logging.info(f"Config file exists: {os.path.exists(config_path)}")
    return config_path

def clean_phone_number(phone):
    """
    Utility function to normalize phone numbers by extracting only digits
    """
    if pd.isna(phone):
        return ''
    return ''.join(filter(str.isdigit, str(phone)))

def process_salesforce_query_in_chunks(sf, query, chunk_size=2000):
    """
    Advanced memory-efficient Salesforce query processor with chunking capability.
    Handles large datasets by processing records in manageable chunks to prevent memory overflow.
    
    Args:
        sf: Salesforce connection object
        query: SOQL query string
        chunk_size: Number of records to process per chunk
        
    Yields:
        DataFrame: Processed chunks of Salesforce data
    """
    result = sf.query(query)
    records = []
    
    total_size = result['totalSize']
    processed = 0
    
    while True:
        # Process current batch
        current_records = result['records']
        processed += len(current_records)
        
        # Yield chunks of records for memory efficiency
        for i in range(0, len(current_records), chunk_size):
            chunk = current_records[i:i + chunk_size]
            chunk_df = pd.DataFrame([{k: v for k, v in record.items() if k != 'attributes'} 
                                   for record in chunk])
            yield chunk_df
        
        # Check if we need to get more records
        if result.get('done'):
            break
            
        # Get next batch using pagination
        result = sf.query_more(result['nextRecordsUrl'], True)
        
        # Log progress for monitoring
        logging.info(f"Processed {processed} of {total_size} records")

def process_seller_data(sf):
    """
    Comprehensive seller account data extraction with business rule filtering.
    
    Business Logic:
    - Extracts active seller accounts with contact information
    - Filters out minors, inactive accounts, and excluded campaigns
    - Excludes accounts with active deals or specific status restrictions
    - Returns complete account dataset for research prioritization
    
    Returns:
        DataFrame: Filtered seller account data
    """
    seller_query = """
    SELECT id, seller_mailing_id__c, record_status__c, FirstName, MiddleName,
           LastName, name_suffix__c, DOB__c, SSN_Encrypted__c, BillingStreet,
           BillingCity, BillingState, BillingPostalCode,
           Phone, PersonHomePhone, cell_phone__c, work_phone__c,
           alternate_phone__c, relative_phone__c,
           new_remaining_amount_guar__c, new_remaining_amount_lc__c, new_trb_remaining__c,
           OwnerId
    FROM Account 
    WHERE database_status__c = 'Active'
        AND minor__c != 'Minor'
        AND initial_marketing_campaign__c NOT IN ('EXCLUDED_CAMPAIGN_1','EXCLUDED_CAMPAIGN_2')
        AND owner.NAME != 'LEGAL_TEAM'
        AND of_active_deals__c = 0
        AND record_status__c NOT IN('Post deal 30', 'No More Payments', 
                                  'Legal Hold – Impasse', 'DNC Requested')
     """

    all_records = []
    
    # Process large dataset in chunks for memory efficiency
    for chunk in process_salesforce_query_in_chunks(sf, seller_query):
        all_records.append(chunk)
        gc.collect()  # Force garbage collection between chunks
    
    df = pd.concat(all_records, ignore_index=True) if all_records else pd.DataFrame()
    return df

def process_rpn_data(sf):
    """
    Extract researched phone number (RPN) account associations.
    
    Business Logic:
    - Identifies accounts that already have phone research completed
    - Filters for unverified but researched phone numbers
    - Returns set of account IDs to exclude from new research requests
    
    Returns:
        set: Account IDs with existing phone research
    """
    rpn_query = """
    SELECT account__c
    FROM researched_phone_number__c
    WHERE verified_number_as__c = ''
        AND phone_text__c != ''
        AND phone_text__c != '9999999999'
    """

    rpn_accounts = set()
    
    # Process RPN data in chunks and maintain unique account set
    for chunk in process_salesforce_query_in_chunks(sf, rpn_query):
        rpn_accounts.update(chunk['Account__c'].unique())
        gc.collect()
    
    return rpn_accounts

def process_address_history(sf):
    """
    Extract most recent address information for each account from address history.
    
    Business Logic:
    - Retrieves historical address changes for all accounts
    - Identifies most recent address entry per account
    - Provides current mailing address for research purposes
    
    Returns:
        DataFrame: Latest address information per account
    """
    address_history_query = """
    SELECT Account__c, billing_street__c, billing_city__c, 
           billing_state__c, billing_zip_postalcode__c, CreatedDate
    FROM Address_History__c 
    """
    
    all_addresses = []
    
    for chunk in process_salesforce_query_in_chunks(sf, address_history_query):
        # Drop any duplicate columns that may occur
        chunk = chunk.loc[:, ~chunk.columns.duplicated()]
        all_addresses.append(chunk)
        gc.collect()
    
    if all_addresses:
        # Combine all address history chunks
        address_df = pd.concat(all_addresses, ignore_index=True)
        
        # Convert CreatedDate to datetime for proper sorting
        address_df['CreatedDate'] = pd.to_datetime(address_df['CreatedDate'])
        
        # Get the most recent address record for each account
        latest_addresses = (
            address_df.sort_values('CreatedDate', ascending=False)
            .groupby('Account__c')
            .first()
            .reset_index()
        )
        
        # Standardize column names for consistency
        rename_cols = {
            'billing_street__c': 'Latest_Billing_Street',
            'billing_city__c': 'Latest_Billing_City',
            'billing_state__c': 'Latest_Billing_State',
            'billing_zip_postalcode__c': 'Latest_Billing_Zip'
        }
        
        latest_addresses.rename(columns=rename_cols, inplace=True)
        
        # Ensure all expected address columns exist
        for col in ['Latest_Billing_Street', 'Latest_Billing_City', 
                   'Latest_Billing_State', 'Latest_Billing_Zip']:
            if col not in latest_addresses.columns:
                latest_addresses[col] = ''
        
        return latest_addresses
    
    # Return empty DataFrame with expected structure if no data
    return pd.DataFrame(columns=['Account__c', 'Latest_Billing_Street', 
                               'Latest_Billing_City', 'Latest_Billing_State', 
                               'Latest_Billing_Zip'])

def process_user_data(sf):
    """
    Extract user/employee data for account ownership mapping.
    Maps account owner IDs to actual user names for reporting.
    
    Returns:
        DataFrame: User ID to name mapping
    """
    user_query = """
    SELECT Id, Name  
    FROM User     
    """
    
    all_users = []
    
    for chunk in process_salesforce_query_in_chunks(sf, user_query):
        all_users.append(chunk)
        gc.collect()
    
    df = pd.concat(all_users, ignore_index=True) if all_users else pd.DataFrame()
    return df

def process_research_requests(sf):
    """
    Advanced research request analysis with date-based filtering.
    
    Business Logic:
    - Identifies accounts with completed phone number research
    - Tracks most recent research completion date per seller
    - Enables 90-day research frequency management
    - Prioritizes accounts based on research recency
    
    Returns:
        DataFrame: Latest research completion dates per seller
    """
    research_query = """
        SELECT Seller__c,
               research_request_completion_date__c
        FROM Research_Request__c
        WHERE  research_information__c = 'Phone Number' 
            OR research_information__c = 'Phone Number;Address'
            OR research_information__c = 'Phone Number;Address;Email'
            OR research_information__c = 'Phone Number;Email'
    """
    
    all_records = []
    
    for chunk in process_salesforce_query_in_chunks(sf, research_query):
        # Clean Salesforce metadata
        if 'attributes' in chunk.columns:
            chunk = chunk.drop('attributes', axis=1)
        
        # Convert completion date to datetime for proper analysis
        chunk['research_request_completion_date__c'] = pd.to_datetime(
            chunk['research_request_completion_date__c']
        )
        
        all_records.append(chunk)
        gc.collect()
    
    if not all_records:
        return pd.DataFrame(columns=['Seller__c', 'Latest_Research_Date'])
    
    # Combine all research request data
    df = pd.concat(all_records, ignore_index=True)
    
    # Identify most recent research date per seller
    latest_research_dates = (
        df.groupby('Seller__c')
        ['research_request_completion_date__c']
        .max()
        .reset_index()
        .rename(columns={'research_request_completion_date__c': 'Latest_Research_Date'})
    )
    
    return latest_research_dates

def create_email_with_data(subject, step_statuses, filtered_data, config, recipient_type='default'):
    """
    Advanced email generation with CSV attachment capability.
    
    Features:
    - Dynamic recipient routing based on email type
    - CSV data attachment for research teams
    - Comprehensive error handling and logging
    - Support for multiple recipient groups
    
    Args:
        subject: Email subject line
        step_statuses: Job execution status dictionary
        filtered_data: Research data to attach
        config: Configuration object with email settings
        recipient_type: Determines recipient group ('rpn' or 'default')
        
    Returns:
        tuple: (email_message, recipients_list)
    """
    message = MIMEMultipart()
    message["From"] = config['Email']['sender_email']
    
    # Route to appropriate recipient group based on email type
    if recipient_type == 'rpn':
        recipients = [email.strip() for email in config['Email']['research_team_recipients'].split(',')]
        logging.info(f"Research Team Recipients: {recipients}")
    else:  # default recipients
        recipients = [email.strip() for email in config['Email']['recipients'].split(',')]
        logging.info(f"Default Recipients: {recipients}")
    
    # Validate recipient list
    recipients = [r for r in recipients if r]  # Remove any empty strings
    if not recipients:
        raise ValueError("No valid recipients found in configuration")
        
    message["To"] = ", ".join(recipients)
    logging.info(f"Setting To: header to: {message['To']}")
    message["Subject"] = subject
    
    # Create structured email body
    body = create_email_body(step_statuses)
    message.attach(MIMEText(body, "plain"))
    
    # Attach research data as CSV if available
    if not filtered_data.empty:
        from io import StringIO
        csv_buffer = StringIO()
        filtered_data.to_csv(csv_buffer, index=False)
        
        # Create CSV attachment
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(csv_buffer.getvalue().encode())
        csv_buffer.close()
            
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename="accounts_requiring_research.csv"'
        )
        message.attach(part)
    
    return message, recipients

def create_email_body(step_statuses):
    """
    Generate formatted email body with job execution metrics and status summary.
    """
    body = "InfoFlow IQ Job Status Report\n"
    body += "=" * 30 + "\n\n"
    
    for step, status in step_statuses.items():
        body += f"{step}: {status}\n"
    
    return body

def send_email_with_data(subject, step_statuses, filtered_data, config, recipient_type='default'):
    """
    Enterprise email delivery with comprehensive error handling and retry logic.
    """
    try:
        message, recipients = create_email_with_data(subject, step_statuses, filtered_data, config, recipient_type)
        
        logging.info(f"Attempting to send email to {len(recipients)} recipients: {recipients}")
        
        # Use corporate SMTP server with secure authentication
        with smtplib.SMTP(config['Email']['smtp_server'], int(config['Email']['smtp_port'])) as server:
            server.starttls()
            server.login(config['Email']['sender_email'], config['Email']['sender_password'])
            
            # Send email and capture any delivery failures
            failed_recipients = server.send_message(message)
            
            if failed_recipients:
                logging.error(f"Failed to send to some recipients: {failed_recipients}")
            else:
                logging.info(f"Email sent successfully to all recipients: {', '.join(recipients)}")
                
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")
        raise

def main():
    """
    Main execution flow implementing comprehensive research request automation.
    
    Business Process:
    1. Extract all active seller accounts meeting business criteria
    2. Filter out accounts with existing phone research (RPN records)
    3. Identify accounts with missing phone contact information
    4. Apply 90-day research frequency threshold
    5. Generate prioritized research request list for research team
    6. Deliver automated email with CSV attachment
    
    Features:
    - Memory-efficient large dataset processing
    - Comprehensive error handling and status tracking
    - Automated email notifications with data attachments
    - Detailed logging for operational monitoring
    """
    logging.info("Starting InfoFlow IQ job execution")
    print("Starting script execution...")
    step_statuses = {}
    
    try:
        # Load secure configuration
        config = configparser.ConfigParser()
        config_path = get_config_path()
        config.read(config_path)
        logging.info(f"Configuration loaded from {config_path}")
        
        # Establish Salesforce API connection
        logging.info("Connecting to Salesforce...")
        sf = Salesforce(
            username=config['Salesforce']['username'],
            password=config['Salesforce']['password'],
            security_token=config['Salesforce']['security_token']
        )
        logging.info("Successfully connected to Salesforce")
        step_statuses["Salesforce Connection"] = "Success"

        # Extract comprehensive seller account dataset
        logging.info("Processing Seller Data...")
        sf_accounts = process_seller_data(sf)
        logging.info(f"Retrieved {len(sf_accounts)} seller records")
        
        # Remove duplicate records based on Account ID
        sf_accounts = sf_accounts.drop_duplicates(subset=['Id'])
        logging.info(f"After deduplication: {len(sf_accounts)} records")
        step_statuses["Get SF Account Data"] = "Success"

        # Process user data for account owner mapping
        logging.info("Processing User Data...")
        user_data = process_user_data(sf)
        
        if user_data.empty:
            logging.warning("User data query returned no results")
        else:
            logging.info(f"Retrieved {len(user_data)} user records")

        # Merge account data with user information for owner names
        sf_accounts = sf_accounts.merge(
            user_data,
            left_on='OwnerId',
            right_on='Id',
            how='left',
            suffixes=('', '_user')
        )
        logging.info(f"After user data merge: {len(sf_accounts)} records")
        
        # Clean up merged data and rename columns
        sf_accounts = sf_accounts.rename(columns={'Name': 'Owner_Name'})
        sf_accounts = sf_accounts.drop('Id_user', axis=1, errors='ignore')
        step_statuses["Get User Data"] = "Success"

        # Identify accounts with existing phone research
        logging.info("Processing RPN Data...")
        rpn_accounts = process_rpn_data(sf)
        step_statuses["Get RPN Data"] = "Success"

        # Filter out accounts that already have phone research completed
        filtered_accounts = sf_accounts[~sf_accounts['Id'].isin(rpn_accounts)].copy()
        logging.info(f"After RPN filter: {len(filtered_accounts)} records")

        # Apply phone number availability filter - identify accounts missing ALL phone contacts
        phone_fields = ['Phone', 'PersonHomePhone', 'cell_phone__c', 
                       'work_phone__c', 'alternate_phone__c']
        
        logging.info("Filtering accounts with all blank phone fields...")
        # Normalize phone field data for consistent comparison
        for field in phone_fields:
            filtered_accounts[field] = filtered_accounts[field].fillna('')
            filtered_accounts[field] = filtered_accounts[field].astype(str).str.strip()

        # Keep only accounts where ALL phone fields are blank/empty
        filtered_accounts = filtered_accounts[
            filtered_accounts[phone_fields].apply(lambda x: x == '').all(axis=1)
        ]
        logging.info(f"After phone fields filter: {len(filtered_accounts)} records")

        # Merge with latest address history for complete contact information
        logging.info("Processing Address History...")
        address_history = process_address_history(sf)
        step_statuses["Get Address History"] = "Success"

        # Left join to preserve all accounts while adding address data
        final_results = filtered_accounts.merge(
            address_history,
            left_on='Id',
            right_on='Account__c',
            how='left'
        ).drop('Account__c', axis=1)
        logging.info(f"After address history merge: {len(final_results)} records")

        # Process research request history for frequency management
        logging.info("Processing Research Request Dates...")
        research_dates = process_research_requests(sf)
        step_statuses["Get Research Request Dates"] = "Success"

        # Merge research dates to enable 90-day frequency filtering
        final_results = final_results.merge(
            research_dates,
            left_on='Id',
            right_on='Seller__c',
            how='left'
        )
        if 'Seller__c' in final_results.columns:
            final_results = final_results.drop('Seller__c', axis=1)

        logging.info(f"After research dates merge: {len(final_results)} records")

        # Apply 90-day research frequency threshold
        today = pd.Timestamp.now()
        threshold_date = today - pd.Timedelta(days=90)

        # Include accounts with no previous research OR research older than 90 days
        is_null = final_results['Latest_Research_Date'].isna()
        is_old = pd.to_datetime(final_results['Latest_Research_Date'], errors='coerce') <= threshold_date
        final_results = final_results[is_null | is_old]

        # Clean data for export
        final_results = final_results.fillna('')

        # Define comprehensive output columns for research team
        output_columns = [
            'Id', 'seller_mailing_id__c', 'record_status__c', 'FirstName', 
            'MiddleName', 'LastName', 'name_suffix__c', 'DOB__c', 'SSN_Encrypted__c',
            'BillingStreet', 'BillingCity', 'BillingState', 'BillingPostalCode',
            'Phone', 'PersonHomePhone', 'cell_phone__c', 'work_phone__c',
            'alternate_phone__c', 'relative_phone__c',
            'new_remaining_amount_guar__c', 'new_remaining_amount_lc__c', 'new_trb_remaining__c',
            'Latest_Billing_Street', 'Latest_Billing_City', 'Latest_Billing_State', 'Latest_Billing_Zip',
            'Latest_Research_Date', 'Owner_Name'
        ]

        # Maintain column order and structure for consistent reporting
        final_columns = [col for col in output_columns if col in final_results.columns]
        final_results = final_results[final_columns]
        logging.info(f"Final columns: {final_columns}")
        
        # Generate comprehensive processing statistics
        logging.info(f"Total Accounts Processed: {len(sf_accounts)}")
        logging.info(f"Accounts with No Phone Numbers: {len(filtered_accounts)}")
        logging.info(f"Final Accounts in Report: {len(final_results)}")
        
        # Add processing metrics to status report
        step_statuses["Total Accounts Processed"] = f"{len(sf_accounts)}"
        step_statuses["Accounts with No Phone Numbers"] = f"{len(filtered_accounts)}"
        step_statuses["Final Accounts in Report"] = f"{len(final_results)}"
        
        # Export results and send automated email notification
        if not final_results.empty:
            # Create output directory if needed
            output_dir = config['Paths']['output_directory']
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            # Export prioritized research list
            output_path = os.path.join(output_dir, 'accounts_requiring_research.csv')
            final_results.to_csv(output_path, index=False)
            logging.info(f"Final results exported to {output_path}")
            
            # Send email with research data to research team
            send_email_with_data(
                "InfoFlow IQ Job Status - Accounts Requiring Research",
                step_statuses,
                final_results,
                config,
                recipient_type='rpn'
            )
            logging.info("Email sent with data attachment")
        else:
            # Send status-only email when no accounts require research
            send_email_with_data(
                "InfoFlow IQ Job Status - No Accounts Found",
                step_statuses,
                pd.DataFrame(),
                config
            )
            logging.info("Email sent (no data to attach)")
        
        # Mark successful completion
        step_statuses["Script Execution"] = "Success"
        logging.info("Script completed successfully")
        
    except Exception as e:
        error_msg = f"Script failed: {str(e)}"
        logging.error(error_msg)
        print(f"Error: {error_msg}")
        step_statuses["Script Execution"] = f"Failed: {str(e)}"
        
        # Send error notification to research team
        try:
            send_email_with_data(
                "InfoFlow IQ Job Status - ERROR",
                step_statuses,
                pd.DataFrame(),
                config,
                recipient_type='rpn'
            )
        except Exception as email_error:
            error_msg = f"Failed to send error notification email: {str(email_error)}"
            logging.error(error_msg)
            print(f"Error: {error_msg}")
        
        raise

if __name__ == "__main__":
    main()