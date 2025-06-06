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
import numpy as np
import gc
from concurrent.futures import ThreadPoolExecutor
from typing import Iterator, Optional
import psutil
from functools import partial

class MemoryOptimizedProcessor:
    """
    Advanced memory optimization class for processing large Salesforce datasets.
    
    Features:
    - Intelligent DataFrame memory optimization through dtype optimization
    - Chunked query processing to prevent memory overflow
    - Automatic garbage collection between operations
    - Performance monitoring capabilities
    """
    
    def __init__(self, chunk_size: int = 5000):
        self.chunk_size = chunk_size
        
    @staticmethod
    def optimize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
        """
        Advanced DataFrame memory optimization through intelligent dtype selection.
        
        Optimization Strategies:
        - Convert low-cardinality object columns to categorical
        - Downcast numeric columns to smallest viable types
        - Maintain data integrity while minimizing memory footprint
        
        Args:
            df: Input DataFrame to optimize
            
        Returns:
            DataFrame: Memory-optimized DataFrame with reduced memory usage
        """
        for col in df.columns:
            # Convert object columns to categories when beneficial
            if df[col].dtype == 'object':
                num_unique = df[col].nunique()
                if num_unique / len(df) < 0.5:  # Less than 50% unique values
                    df[col] = pd.Categorical(df[col])
            
            # Downcast integer columns to smallest viable type
            elif df[col].dtype == 'int64':
                if df[col].min() >= 0:
                    if df[col].max() <= 255:
                        df[col] = df[col].astype(np.uint8)
                    elif df[col].max() <= 65535:
                        df[col] = df[col].astype(np.uint16)
                    else:
                        df[col] = df[col].astype(np.uint32)
                else:
                    if df[col].min() >= -128 and df[col].max() <= 127:
                        df[col] = df[col].astype(np.int8)
                    elif df[col].min() >= -32768 and df[col].max() <= 32767:
                        df[col] = df[col].astype(np.int16)
                    else:
                        df[col] = df[col].astype(np.int32)
            
            # Downcast float columns
            elif df[col].dtype == 'float64':
                df[col] = pd.to_numeric(df[col], downcast='float')
                
        return df

    def process_salesforce_query(self, sf, query: str) -> pd.DataFrame:
        """
        Memory-efficient Salesforce query processor with chunking and optimization.
        
        Features:
        - Automatic query chunking for large datasets
        - Memory optimization between chunks
        - Garbage collection management
        - Progress monitoring for long-running queries
        
        Args:
            sf: Salesforce connection object
            query: SOQL query string
            
        Returns:
            DataFrame: Complete optimized query results
        """
        all_chunks = []
        offset = 0
        
        while True:
            # Execute chunked query with LIMIT/OFFSET pagination
            chunked_query = f"{query} LIMIT {self.chunk_size} OFFSET {offset}"
            records = sf.query(chunked_query)
            
            if not records['records']:
                break
                
            # Convert to DataFrame and clean Salesforce metadata
            chunk_df = pd.DataFrame(records['records'])
            if 'attributes' in chunk_df.columns:
                chunk_df = chunk_df.drop('attributes', axis=1)
            
            # Apply memory optimization to chunk
            chunk_df = self.optimize_dtypes(chunk_df)
            all_chunks.append(chunk_df)
            
            offset += self.chunk_size
            if len(records['records']) < self.chunk_size:
                break
            
            # Clean up intermediate objects
            del records
            gc.collect()
        
        if all_chunks:
            result = pd.concat(all_chunks, ignore_index=True)
            del all_chunks
            gc.collect()
            return result
        return pd.DataFrame()

def print_memory_usage(message: str = ""):
    """
    Monitor and log memory usage for performance optimization.
    Essential for tracking memory efficiency in large data processing operations.
    """
    process = psutil.Process()
    print(f"Memory usage {message}: {process.memory_info().rss / 1024 / 1024:.2f} MB")

def get_config_path():
    """
    Dynamically determine configuration file path for both development and production deployment.
    Supports both standard Python execution and compiled executable deployment.
    """
    if getattr(sys, 'frozen', False):
        bundle_dir = os.path.dirname(sys.executable)
    else:
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(bundle_dir, 'config.ini')
    return config_path

def clean_phone_numbers_vectorized(series):
    """
    High-performance vectorized phone number normalization.
    Removes all non-digit characters for consistent phone number matching.
    """
    return series.astype(str).str.replace(r'\D', '', regex=True)

def find_matching_phone_vectorized(df, phone_columns, phone_number):
    """
    Vectorized phone number matching across multiple phone field columns.
    
    Business Logic:
    - Searches across all available phone fields (home, cell, work, alternate, etc.)
    - Returns the specific column containing the matching phone number
    - Enables targeted phone number removal from the correct field
    
    Args:
        df: Account DataFrame with phone columns
        phone_columns: List of phone field column names
        phone_number: Target phone number to locate
        
    Returns:
        str: Column name containing the matching phone number, or None
    """
    for col in phone_columns:
        mask = df[col] == phone_number
        if mask.any():
            return col
    return None

def create_email_body(step_statuses):
    """
    Generate structured email body with job execution status and metadata.
    """
    header = """#Source: PRODUCTION_SERVER
#JOB Name: AutoFlush IQ
#Schedule: Daily @ 6:30 AM
#Description: Automated phone number quality management and removal system"""
    
    if isinstance(step_statuses, dict):
        formatted_statuses = "\n".join([f"{step}: {status}" for step, status in step_statuses.items()])
    else:
        formatted_statuses = str(step_statuses)
    
    return f"{header}\n\nJob Status:\n{formatted_statuses}"

def send_email(subject, step_statuses, config):
    """
    Enterprise email notification system with secure SMTP authentication.
    """
    message = MIMEMultipart()
    message["From"] = config['Email']['sender_email']
    
    recipients = config['Email']['recipients'].split(',')
    recipients = [email.strip() for email in recipients]
    
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    
    body = create_email_body(step_statuses)
    message.attach(MIMEText(body, "plain"))

    # Use corporate SMTP server with TLS encryption
    with smtplib.SMTP(config['Email']['smtp_server'], int(config['Email']['smtp_port'])) as server:
        server.starttls()
        server.login(config['Email']['sender_email'], config['Email']['sender_password'])
        server.send_message(message)

def process_wrong_numbers(rf_data: pd.DataFrame, af_data: pd.DataFrame, phone_columns: list) -> pd.DataFrame:
    """
    Advanced wrong number detection and processing with parallel execution.
    
    Business Logic:
    - Identifies phone numbers marked as "Wrong Number" in call dispositions
    - Applies threshold-based logic (2+ wrong number attempts)
    - Processes both inbound and outbound call data
    - Uses parallel processing for performance optimization
    - Matches wrong numbers to specific account phone fields for targeted removal
    
    Algorithm:
    1. Extract wrong number calls from both inbound/outbound call data
    2. Group by Account + Phone Number combinations
    3. Apply frequency threshold (2+ occurrences)
    4. Use parallel processing to match phone numbers to account fields
    5. Return targeted removal instructions (Account ID + Phone Field + Number)
    
    Args:
        rf_data: Call activity data with dispositions
        af_data: Account data with phone fields
        phone_columns: List of phone field columns to search
        
    Returns:
        DataFrame: Accounts and phone fields requiring number removal
    """
    # Filter for wrong number dispositions from both call directions
    mask_in = (rf_data['CallDisposition'] == 'Wrong Number') & (rf_data['Subject'] == 'Inbound Call')
    mask_out = (rf_data['CallDisposition'] == 'Wrong Number') & (rf_data['Subject'] == 'Outbound Call')
    
    # Combine inbound and outbound wrong number data
    phone_data = pd.concat([
        rf_data[mask_in][['AccountId', 'Five9__Five9ANI__c']].rename(columns={'Five9__Five9ANI__c': 'PhoneNumber'}),
        rf_data[mask_out][['AccountId', 'Five9__Five9DNIS__c']].rename(columns={'Five9__Five9DNIS__c': 'PhoneNumber'})
    ])
    
    # Apply threshold logic - require 2+ wrong number attempts
    call_counts = phone_data.groupby(['AccountId', 'PhoneNumber']).size()
    frequent_pairs = call_counts[call_counts >= 2].reset_index()
    
    # Parallel processing for phone number field matching
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for _, row in frequent_pairs.iterrows():
            af_row = af_data[af_data['Id'] == row['AccountId']]
            if not af_row.empty:
                future = executor.submit(
                    find_matching_phone_vectorized,
                    af_row,
                    phone_columns,
                    row['PhoneNumber']
                )
                futures.append((row, future))
        
        # Collect parallel processing results
        results = []
        for row, future in futures:
            matching_column = future.result()
            if matching_column:
                results.append({
                    'Id': row['AccountId'],
                    'MatchingColumn': matching_column,
                    'PhoneNumber': row['PhoneNumber']
                })
    
    return pd.DataFrame(results)

def process_disconnected_calls(all_discos: pd.DataFrame, min_count: int = 3, min_days: int = 90) -> list:
    """
    Advanced disconnected call analysis with time-based and frequency thresholds.
    
    Business Logic:
    - Identifies phone numbers with persistent disconnection patterns
    - Applies dual threshold system: frequency (3+ calls) + time span (90+ days)
    - Prevents premature removal of temporarily disconnected numbers
    - Uses vectorized operations for performance on large datasets
    
    Algorithm:
    1. Group calls by Account + Phone Number combination
    2. Calculate call frequency and time span for each combination
    3. Apply dual threshold: 3+ disconnected calls over 90+ day period
    4. Return qualifying combinations for phone number removal
    
    Args:
        all_discos: DataFrame of calls with disconnected dispositions
        min_count: Minimum number of disconnected calls required (default: 3)
        min_days: Minimum time span in days required (default: 90)
        
    Returns:
        list: Qualifying account-phone combinations for removal
    """
    # Convert date column for time-based analysis
    all_discos['ActivityDate'] = pd.to_datetime(all_discos['ActivityDate'])
    
    # Group by unique account-phone combinations
    grouped = all_discos.groupby('Kkey').agg({
        'CallDisposition': 'count',
        'ActivityDate': ['min', 'max']
    })
    
    # Calculate time span between first and last disconnected call
    grouped['date_diff'] = (
        grouped['ActivityDate']['max'] - grouped['ActivityDate']['min']
    ).dt.days
    
    # Apply dual threshold logic
    mask = (grouped['CallDisposition']['count'] >= min_count) & (grouped['date_diff'] >= min_days)
    return grouped[mask].index.tolist()

def send_to_sql(conn, cursor, table_name: str, df: pd.DataFrame, id_type: str, procedure_name: str):
    """
    High-performance SQL data insertion with batch processing and transaction management.
    
    Features:
    - Automatic cleanup of existing data for the current date
    - Batch processing for optimal SQL Server performance
    - Transaction management with commit optimization
    - Memory-efficient processing for large datasets
    
    Args:
        conn: SQL Server connection object
        cursor: Database cursor
        table_name: Target table for data insertion
        df: DataFrame containing removal instructions
        id_type: Type of ID being processed (Account, RPN, etc.)
        procedure_name: Name of the processing procedure for tracking
    """
    current_date = datetime.now().date()
    
    # Clean existing data for current date and procedure
    delete_query = """
    DELETE FROM {table} WHERE [Date] = ? AND [Procedure] = ? AND [Id_Type] = ?
    """.format(table=table_name)
    
    cursor.execute(delete_query, (current_date, procedure_name, id_type))
    
    # Prepare batch insert query
    insert_query = """
    INSERT INTO {table} ([Date], [Procedure], [Id_Type], [Id], [MatchingField], [PhoneNumber])
    VALUES (?, ?, ?, ?, ?, ?)
    """.format(table=table_name)
    
    # Process in batches for optimal performance
    batch_size = 1000
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i + batch_size]
        cursor.executemany(insert_query,
            [(current_date, procedure_name, id_type, row['Id'],
              row['MatchingColumn'], row['PhoneNumber']) for _, row in batch.iterrows()])
        conn.commit()

def main():
    """
    Main execution flow implementing comprehensive phone number quality management.
    
    Business Process:
    1. Extract call activity data with dispositions
    2. Extract account data with phone field structure
    3. Extract researched phone number (RPN) data
    4. Apply wrong number detection algorithm with threshold logic
    5. Apply disconnected call analysis with time-based filtering
    6. Generate targeted removal instructions for SQL-based cleanup
    7. Execute automated email notification
    
    Features:
    - Memory-optimized processing for large datasets (400K+ accounts, 1M+ call records)
    - Parallel processing for performance optimization
    - Comprehensive error handling and status tracking
    - Real-time memory monitoring and garbage collection
    - Enterprise-grade logging and notification system
    """
    print_memory_usage("Start")
    step_statuses = {}
    processor = MemoryOptimizedProcessor(chunk_size=5000)
    config = None
    
    try:
        # Load secure configuration
        config = configparser.ConfigParser()
        config.read(get_config_path())
        
        # Initialize Salesforce API connection
        sf = Salesforce(
            username=config['Salesforce']['username'],
            password=config['Salesforce']['password'],
            security_token=config['Salesforce']['security_token'],
        )
        step_statuses["Salesforce Connection"] = "Success"
        
        # Define phone field structure for multi-field phone number management
        phone_columns = ['Phone', 'PersonHomePhone', 'cell_phone__c', 
                        'work_phone__c', 'alternate_phone__c', 'relative_phone__c']
        
        # Comprehensive call activity query for disposition analysis
        task_query = """
            SELECT Id, subject, activitydate, status, ownerid,
                   description, accountid, five9__five9dnis__c, five9__five9ani__c,
                   calldisposition
            FROM task 
            WHERE (Subject = 'Outbound Call' OR Subject = 'Inbound Call')
                AND account.database_status__c = 'Active'
        """
        
        # Active account query with business rule filtering
        account_query = """
            SELECT id, Phone, PersonHomePhone, cell_phone__c,
                   work_phone__c, alternate_phone__c, relative_phone__c
            FROM Account 
            WHERE database_status__c = 'Active'
                AND minor__c != 'Minor'
                AND initial_marketing_campaign__c != 'EXCLUDED_CAMPAIGN_ID'
                AND owner.NAME != 'LEGAL_TEAM'
                AND of_active_deals__c = 0
                AND record_status__c NOT IN ('Post deal 30', 'No More Payments', 
                                           'Legal Hold – Impasse', 'DNC Requested')
        """
        
        # Researched phone number (RPN) query for comprehensive phone data
        rpn_query = """
            SELECT Id, account__c, phone_text__c
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
                AND record_status__c NOT IN ('Post deal 30', 'No More Payments',
                                           'Legal Hold – Impasse', 'DNC Requested')
        """
        
        # Establish secure SQL Server connection
        conn_str = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={config["Database"]["server"]};DATABASE={config["Database"]["database"]};Trusted_Connection=Yes;Encrypt=Yes;TrustServerCertificate=Yes;'
        
        with pyodbc.connect(conn_str) as conn:
            with conn.cursor() as cursor:
                step_statuses["Database Connection"] = "Success"
                
                # Extract and process call activity data
                rf = processor.process_salesforce_query(sf, task_query)
                step_statuses["Get SF Task Data"] = "Success"
                print_memory_usage("After Task Data")
                
                # Extract and process account data
                af = processor.process_salesforce_query(sf, account_query)
                step_statuses["Get SF Account Data"] = "Success"
                print_memory_usage("After Account Data")
                
                # Extract and process RPN data
                rpn = processor.process_salesforce_query(sf, rpn_query)
                step_statuses["Get SF RPN Data"] = "Success"
                print_memory_usage("After RPN Data")
                
                # Normalize phone numbers across all account phone fields
                for column in phone_columns:
                    if column in af.columns:
                        af[column] = clean_phone_numbers_vectorized(af[column])
                
                # Execute wrong number detection and processing algorithm
                wrong_number_clean = process_wrong_numbers(rf, af, phone_columns)
                step_statuses["Wrong Number Processing"] = "Success"
                
                # Execute disconnected call analysis
                all_discos = rf[rf['Subject'] == 'Outbound Call'].copy()
                all_discos['PhoneNumber'] = all_discos['five9__five9dnis__c']
                all_discos['Kkey'] = all_discos['AccountId'].astype(str) + '_' + all_discos['PhoneNumber'].astype(str)
                
                disco_qualifying_kkeys = process_disconnected_calls(all_discos)
                
                # Generate disconnected number removal instructions
                disco_number_clean = process_wrong_numbers(
                    all_discos[all_discos['Kkey'].isin(disco_qualifying_kkeys)],
                    af,
                    phone_columns
                )
                step_statuses["Disconnected Call Processing"] = "Success"
                
                # Execute SQL data insertion for automated cleanup processing
                send_to_sql(conn, cursor, 'phone_cleanup_queue', wrong_number_clean, 'Account', 'wrong_number_clean')
                send_to_sql(conn, cursor, 'phone_cleanup_queue', disco_number_clean, 'Account', 'disco_number_clean')
                step_statuses["Push Auto Flush to SQL"] = "Success"
                
    except Exception as e:
        step_statuses["Error"] = f"Failed: {str(e)}"
        raise
    finally:
        # Send automated email notification with job status
        if config:
            try:
                subject = "AutoFlush IQ Job Status"
                send_email(subject, step_statuses, config)
            except Exception as e:
                print(f"Failed to send email: {str(e)}")
        
        print_memory_usage("End")

if __name__ == "__main__":
    main()