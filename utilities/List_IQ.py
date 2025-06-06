from simple_salesforce import Salesforce
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pyodbc 
import configparser
import os
import sys

#############################
# BEGIN Function Definitions#
#############################

def get_config_path():
    """
    Dynamically determine configuration file path for both development and production deployment.
    Supports both standard Python execution and compiled executable deployment.
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        bundle_dir = os.path.dirname(sys.executable)
    else:
        # Running as Python script
        bundle_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(bundle_dir, 'config.ini')
    print(f"Looking for config file at: {config_path}")
    print(f"Config file exists: {os.path.exists(config_path)}")
    return config_path

def export_dataframe_to_csv(df, file_path):
    """
    Export DataFrame to CSV with proper formatting for dialer system consumption.
    """
    df.to_csv(file_path, index=False)

def create_email_body(step_statuses):
    """
    Generate structured email body with comprehensive job execution status and visual indicators.
    
    Features:
    - Clear success/failure indicators with visual symbols
    - Detailed step-by-step execution status
    - Professional formatting for operational monitoring
    """
    header = """#Source: PRODUCTION_SERVER
#JOB Name:  List IQ - Geographic Call List Generator
#Description: Automated call list generation with census-based geographic optimization
"""
    
    if isinstance(step_statuses, dict):
        # Analyze execution status across all steps
        has_failure = any("Failed" in str(status) for status in step_statuses.values())
        
        # Add clear visual status indicator
        status_indicator = "❌ JOB FAILED" if has_failure else "✓ JOB COMPLETED SUCCESSFULLY"
        formatted_statuses = "\n".join([f"{step}: {status}" for step, status in step_statuses.items()])
        
    elif isinstance(step_statuses, str):
        status_indicator = "❌ JOB FAILED" if "Failed" in step_statuses else "✓ JOB COMPLETED SUCCESSFULLY"
        formatted_statuses = step_statuses
    else:
        status_indicator = "❌ JOB STATUS UNKNOWN"
        formatted_statuses = "Error: Invalid step_statuses format"
    
    return f"{header}\n\n{status_indicator}\n\nJob Status:\n{formatted_statuses}"

def send_email(subject, step_statuses):
    """
    Enterprise email notification system with comprehensive error handling and retry logic.
    
    Features:
    - Automatic subject line modification for error conditions
    - SMTP retry logic for reliability
    - Multi-recipient support from configuration
    - Secure authentication with corporate email server
    """
    try:
        # Create structured email message
        message = MIMEMultipart()
        message["From"] = config['Email']['sender_email']
        
        # Parse recipient list from configuration
        recipients = config['Email']['recipients'].split(',')
        recipients = [email.strip() for email in recipients]  # Remove whitespace
        
        # Set recipient field
        message["To"] = ", ".join(recipients)
        
        # Modify subject line based on execution status
        if isinstance(step_statuses, dict):
            has_failure = any("Failed" in str(status) for status in step_statuses.values())
        else:
            has_failure = "Failed" in str(step_statuses)
            
        if has_failure:
            subject = f"ERROR - {subject}"
        
        message["Subject"] = subject
        
        # Generate formatted email body
        body = create_email_body(step_statuses)
        message.attach(MIMEText(body, "plain"))

        # Execute SMTP transmission with retry logic
        try:
            with smtplib.SMTP(config['Email']['smtp_server'], int(config['Email']['smtp_port'])) as server:
                server.starttls()
                server.login(config['Email']['sender_email'], config['Email']['sender_password'])
                server.send_message(message)
                print("Email sent successfully")
        except Exception as smtp_error:
            print(f"Failed to send email: {smtp_error}")
            # Implement retry mechanism for critical notifications
            with smtplib.SMTP(config['Email']['smtp_server'], int(config['Email']['smtp_port'])) as server:
                server.starttls()
                server.login(config['Email']['sender_email'], config['Email']['sender_password'])
                server.send_message(message)
                print("Email sent successfully on second attempt")
                
    except Exception as e:
        print(f"Error in send_email function: {e}")

##########################
#END Function Definitions#
##########################

def main():
    """
    Main execution flow implementing advanced geographic call list optimization.
    
    Business Process:
    1. Extract area code to state mapping from enterprise data warehouse
    2. Query Salesforce for eligible phone numbers with business rule filtering
    3. Apply geographic state-based population distribution algorithm
    4. Implement time-based prioritization (recent vs. historical records)
    5. Generate balanced call list optimized for geographic distribution
    6. Export formatted list for dialer system consumption
    7. Send comprehensive status notification
    
    Advanced Features:
    - Census-based population percentage distribution
    - Configurable contact frequency thresholds
    - Mixed temporal selection algorithm (recent + historical balance)
    - Real-time geographic balancing with overflow handling
    - Enterprise data pipeline integration
    
    Geographic Optimization Algorithm:
    - Uses census data to determine target call volume per state
    - Applies population-based weighting to ensure representative coverage
    - Balances recent records (high priority) with historical records
    - Implements overflow logic to maintain target list size
    - Randomizes final output to prevent systematic bias
    """
    
    # Initialize comprehensive status tracking
    step_statuses = {}
    
    try:
        # Load secure configuration
        global config
        config = configparser.ConfigParser()
        config.read(get_config_path())
        
        # Establish Salesforce API connection
        try:
            sf = Salesforce(
                username=config['Salesforce']['username'],
                password=config['Salesforce']['password'],
                security_token=config['Salesforce']['security_token'],
            )
            step_statuses["Salesforce Connection"] = "Success"
        except Exception as e:
            step_statuses["Salesforce Connection"] = f"Failed: {str(e)}"
            raise

        # Establish enterprise data warehouse connection
        try:
            # Extract database connection parameters from secure configuration
            server = config['Database']['server']
            database = config['Database']['database']
            username = config['Database']['username']
            password = config['Database']['password']

            # Create secure connection string with encryption
            conn_str = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=Yes;Encrypt=Yes;TrustServerCertificate=Yes;'
            conn = pyodbc.connect(conn_str)
            cursor = conn.cursor()

            step_statuses["Data Warehouse Connection"] = "Success"
        except Exception as e:
            step_statuses["Data Warehouse Connection"] = f"Failed: {str(e)}"
            raise

        # Extract area code to state mapping for geographic optimization
        try:
            # Query enterprise reference data for geographic mapping
            sql_query = "SELECT AREA_CODE, ST_ABBRV FROM dim_area_code_to_state_mapping"

            # Execute query and create geographic lookup DataFrame
            ac_df = pd.read_sql(sql_query, conn)

            # Standardize area codes as strings for consistent mapping
            ac_df["AREA_CODE"] = ac_df["AREA_CODE"].astype(str)

            # Create high-performance dictionary lookup for area code resolution
            area_code_to_state = dict(zip(ac_df["AREA_CODE"], ac_df["ST_ABBRV"]))

            step_statuses["Geographic Mapping Data"] = "Success"
        except Exception as e:
            step_statuses["Geographic Mapping Data"] = f"Failed: {str(e)}"
            raise

        # Execute comprehensive Salesforce data extraction with business rule filtering
        try:
            # Get contact frequency threshold from configuration
            contact_days_threshold = int(config['Parameters']['contact_days_threshold'])

            # Complex Salesforce query with advanced business logic filtering
            sf_query = """
            SELECT 
                CreatedDate,
                account_mailing_id__c,
                account__c,
                id,
                account_owner_name__c,
                seller_state__c,
                account_first_name__c,
                account_last_name__c,
                phone_text__c,
                seller_last_contacted_date__c,
                research_record_flag__c,
                disposition_date__c,
                disposition__c
            FROM   researched_phone_number__c
            WHERE  verified_number_as__c = ''
                AND account__r.inactive__c = false
                AND account__r.minor__c = ''
                AND phone_text__c != ''
                AND phone_text__c != '9999999999'
                AND account__r.billingcity != 'EXCLUDED_CITY'
                AND account__r.initial_marketing_campaign__c != 'EXCLUDED_CAMPAIGN_ID'
                AND account__r.owner.user_is_ae__c = 0
                AND account__r.owner.NAME != 'LEGAL_TEAM'
                AND account__r.of_active_deals__c = 0
                AND record_status__c NOT IN( 'Post deal 30', 'No More Payments',
                                                'Legal Hold – Impasse', 'DNC Requested'
                                                )
                AND ( disposition__c = NULL
                        OR disposition__c = 'No Answer'
                        OR disposition__c = 'VM - No Message'
                        OR disposition__c = 'VM - Left Message'
                        OR disposition__c = 'Left Message'
                        OR disposition__c = 'Abandon'
                        OR disposition__c = 'Busy' )
                AND (Last_contacted_Number_of_Days__c > {0} OR CreatedDate = LAST_N_DAYS:{1}) 
                ORDER BY Disposition_Date__c ASC
            """.format(contact_days_threshold, int(config['Parameters']['recent_days_window']))

            # Execute comprehensive Salesforce query
            sf_data = sf.query_all(sf_query)
            
            # Convert Salesforce response to DataFrame
            df = pd.DataFrame([dict(row) for row in sf_data["records"]])
     
            # Remove Salesforce metadata attributes
            rf = df.drop(df.columns[0:1], axis=1)

            # Standardize state abbreviations to uppercase
            rf["Seller_State__c"] = rf["Seller_State__c"].str.upper()

            # Extract area code from phone number for geographic analysis
            rf["area_code"] = rf["Phone_Text__c"].str[:3]

            # Convert area code to string for dictionary lookup
            rf["area_code"] = rf["area_code"].astype(str)

            # Apply geographic mapping using area code lookup
            rf["state_from_area_code"] = rf["area_code"].map(area_code_to_state)

            # Intelligent state resolution: fill missing states using area code mapping
            rf.loc[
                (rf["Seller_State__c"].isna())
                | (rf["Seller_State__c"] == "")
                | (rf["Seller_State__c"] == " "),
                "Seller_State__c",
            ] = rf["state_from_area_code"]

            # Handle any remaining missing state data
            rf["Seller_State__c"] = rf["Seller_State__c"].fillna("")

            # Clean up temporary geographic mapping column
            rf = rf.drop("state_from_area_code", axis=1)

            # Ensure proper datetime formatting for temporal analysis
            if not pd.api.types.is_datetime64_any_dtype(rf["CreatedDate"]):
                rf["CreatedDate"] = pd.to_datetime(rf["CreatedDate"], errors="coerce")

            step_statuses["Salesforce Data Extraction"] = "Success"
        except Exception as e:
            step_statuses["Salesforce Data Extraction"] = f"Failed: {str(e)}"
            raise

        # Implement advanced geographic distribution algorithm using census data
        try:
            # Extract geographic balancing parameters from configuration
            target_total_records = int(config['Parameters']['target_total_records'])
            create_dt_split = float(config['Parameters']['create_dt_split'])

            # Load census-based state population demographics
            spd_path = config['Paths']['state_population_demographics']
            spd_df = pd.read_csv(spd_path)

            # Calculate target call volume per state based on population percentages
            total_per_of_pop = spd_df["PER_OF_POP"].sum()
            spd_df["Target_Count"] = (spd_df["PER_OF_POP"] / total_per_of_pop * target_total_records).round().astype(int)

            # Ensure mathematical precision: total target counts equal target records
            difference = target_total_records - spd_df["Target_Count"].sum()
            spd_df.loc[spd_df["Target_Count"].idxmax(), "Target_Count"] += difference

            # Analyze current geographic distribution of available records
            current_state_counts = rf["Seller_State__c"].value_counts()

            # Calculate optimal selection counts per state with overflow handling
            state_keep_counts = {}
            for state in spd_df["ST_ABBRV"]:
                target_count = spd_df.loc[spd_df["ST_ABBRV"] == state, "Target_Count"].iloc[0]
                current_count = current_state_counts.get(state, 0)

                # Apply intelligent overflow logic: take available vs. target
                if current_count > target_count:
                    state_keep_counts[state] = target_count
                else:
                    state_keep_counts[state] = current_count

            step_statuses["Geographic Distribution Algorithm"] = "Success"
        except Exception as e:
            step_statuses["Geographic Distribution Algorithm"] = f"Failed: {str(e)}"
            raise

        # Execute advanced temporal balancing and list generation
        try:
            # Validate output directory accessibility
            output_path = config['Paths']['output_path']
            if not os.path.exists(output_path):
                raise FileNotFoundError(f"Output directory not accessible: {output_path}")

            # Extract temporal parameters for recent vs. historical balancing
            recent_days_window = int(config['Parameters']['recent_days_window'])

            # Generate timestamped output filename
            current_date = pd.Timestamp.now().strftime('%Y%m%d')

            # Implement advanced temporal prioritization algorithm
            current_time = pd.Timestamp.now(tz='UTC')
            prior_day_cutoff = current_time - pd.Timedelta(days=recent_days_window)
            
            # Separate records into temporal categories for prioritized processing
            recent_mask = rf["CreatedDate"] >= prior_day_cutoff
            recent_records = rf[recent_mask].copy()
            older_records = rf[~recent_mask].copy()

            # Execute geographic balancing algorithm on historical records
            balanced_older = pd.DataFrame()
            
            # Apply state-by-state optimization with mixed temporal selection
            for state in spd_df["ST_ABBRV"]:
                target_count = spd_df.loc[spd_df["ST_ABBRV"] == state, "Target_Count"].iloc[0]
                state_older_data = older_records[older_records["Seller_State__c"] == state]
                
                if len(state_older_data) > target_count:
                    # Implement mixed temporal selection algorithm
                    state_data_sorted = state_older_data.sort_values("CreatedDate", ascending=False)
                    newer_count = int(target_count * create_dt_split)
                    older_count = target_count - newer_count
                    
                    # Select balanced mix of recent and historical records
                    newer_records = state_data_sorted.head(newer_count).sample(frac=1)
                    older_records_pool = state_data_sorted.iloc[newer_count:]
                    older_selected = older_records_pool.sample(n=min(older_count, len(older_records_pool)))
                    
                    selected_records = pd.concat([newer_records, older_selected])
                else:
                    # Use all available records when under target
                    selected_records = state_older_data
                
                balanced_older = pd.concat([balanced_older, selected_records])
            
            # Apply randomization to prevent systematic bias
            balanced_older = balanced_older.sample(frac=1).reset_index(drop=True)
            
            # Combine prioritized recent records with balanced historical records
            balanced_rf = pd.concat([recent_records, balanced_older]).reset_index(drop=True)
            
            # Implement overflow handling: duplicate records if under target
            if len(balanced_rf) < target_total_records:
                records_needed = target_total_records - len(balanced_rf)
                # Only duplicate from historical records to maintain recent record priority
                if len(balanced_older) > 0:
                    duplicates = balanced_older.sample(n=records_needed, replace=True)
                    balanced_rf = pd.concat([balanced_rf, duplicates]).reset_index(drop=True)

            # Generate timestamped output filename for dialer consumption
            output_filename = f"GeographicDialer_{current_date}.csv"
            full_output_path = os.path.join(output_path, output_filename)

            # Generate comprehensive execution summary for operational monitoring
            state_counts = balanced_rf['Seller_State__c'].value_counts().to_dict()
            formatted_state_counts = "\n        ".join([f"{state}: {int(count)}" for state, count in state_counts.items()])

            # Calculate recent record statistics
            recent_records_count = len(balanced_rf[balanced_rf["CreatedDate"] >= prior_day_cutoff])
            
            step_statuses["Geographic Balancing Summary"] = f"""
            Total records: {len(balanced_rf)}
            Recent records (last {recent_days_window} hours): {recent_records_count}
            Percentage of recent records: {(recent_records_count/len(balanced_rf)*100):.2f}%
            Records per state:
            {formatted_state_counts}
            Output file: {output_filename}
            """
            
            # Clean dataset for dialer system consumption
            balanced_rf = balanced_rf.drop(columns=['area_code'])
            balanced_rf = balanced_rf.drop(columns=['CreatedDate'])

            # Execute final export to dialer system
            try:
                export_dataframe_to_csv(balanced_rf, full_output_path)
                step_statuses["Export File"] = f"Successfully exported to: {output_filename}"
            except Exception as export_error:
                raise Exception(f"Failed to export file: {str(export_error)}")

            step_statuses["List Generation Process"] = "Success"
            step_statuses["Overall Job Status"] = "Completed Successfully"

        except Exception as e:
            step_statuses["List Generation Process"] = f"Failed: {str(e)}"
            step_statuses["Overall Job Status"] = f"Failed: {str(e)}"
            raise

    finally:
        # Ensure proper database connection cleanup
        if 'conn' in locals() and conn:
            conn.close()
            step_statuses["Database Connection"] = "Closed"

        # Send comprehensive status notification
        try:
            subject = "List IQ - Geographic Call List Generator Status"
            
            # Format status information for email transmission
            if isinstance(step_statuses, dict):
                status_str = "\n".join([f"{step}: {status}" for step, status in step_statuses.items()])
            else:
                status_str = str(step_statuses)
            
            send_email(subject, status_str)
        except Exception as e:
            # Graceful handling of email notification failures
            pass  # Log this error if logging framework is implemented

if __name__ == "__main__":
    main()