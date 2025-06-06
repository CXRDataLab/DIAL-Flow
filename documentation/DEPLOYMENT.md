# DIAL-Flow Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying and configuring the DIAL-Flow automation suite in production environments. The system supports both development and production deployments with secure configuration management.

---

## System Requirements

### Hardware Requirements

**Minimum Specifications:**
- **CPU:** 4 cores, 2.4 GHz
- **RAM:** 8 GB (16 GB recommended for large datasets)
- **Storage:** 50 GB available space
- **Network:** Stable internet connection for API access

**Recommended Production Specifications:**
- **CPU:** 8 cores, 3.0 GHz
- **RAM:** 32 GB
- **Storage:** 100 GB SSD
- **Network:** High-speed corporate network with API access

### Software Requirements

**Operating System:**
- Windows Server 2016+ (recommended)
- Windows 10+ (development)
- Linux (Ubuntu 18.04+, CentOS 7+)

**Python Environment:**
- Python 3.8 or higher
- pip package manager
- Virtual environment support

**Database Requirements:**
- SQL Server 2016+ with ODBC Driver 18
- Appropriate database permissions for read/write operations

**External Dependencies:**
- Salesforce API access with appropriate user permissions
- SMTP server access for email notifications
- Network file share access (if using shared configuration)

---

## Installation Guide

### 1. Python Environment Setup

```bash
# Create virtual environment
python -m venv dial_flow_env

# Activate virtual environment
# Windows:
dial_flow_env\Scripts\activate
# Linux/Mac:
source dial_flow_env/bin/activate

# Upgrade pip
python -m pip install --upgrade pip
```

### 2. Required Python Packages

```bash
# Install required packages
pip install simple-salesforce==1.12.2
pip install pandas==1.5.3
pip install pyodbc==4.0.35
pip install numpy==1.24.3
pip install psutil==5.9.4
pip install configparser==5.3.0

# For development/testing
pip install pytest==7.2.1
pip install jupyter==1.0.0
```

### 3. Database Driver Installation

**Windows - SQL Server ODBC Driver:**
```powershell
# Download and install ODBC Driver 18 for SQL Server
# https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

# Verify installation
odbcad32.exe
```

**Linux - SQL Server ODBC Driver:**
```bash
# Ubuntu/Debian
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list
apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql18

# CentOS/RHEL
curl https://packages.microsoft.com/config/rhel/8/prod.repo > /etc/yum.repos.d/mssql-release.repo
yum remove unixODBC-utf16 unixODBC-utf16-devel
ACCEPT_EULA=Y yum install -y msodbcsql18
```

---

## Configuration Management

### Configuration File Structure

Create a `config.ini` file with the following structure:

```ini
[Salesforce]
username = YOUR_SALESFORCE_USERNAME
password = YOUR_SALESFORCE_PASSWORD
security_token = YOUR_SALESFORCE_SECURITY_TOKEN

[Database]
server = YOUR_SQL_SERVER
database = YOUR_DATABASE_NAME
username = YOUR_DB_USERNAME
password = YOUR_DB_PASSWORD

[Email]
sender_email = automation@yourcompany.com
sender_password = YOUR_EMAIL_PASSWORD
smtp_server = smtp.yourcompany.com
smtp_port = 587
recipients = team@yourcompany.com,manager@yourcompany.com
research_team_recipients = research@yourcompany.com

[Paths]
dedupe_output_path = C:\DIAL_Flow\Output\dedupe_results.csv
output_directory = C:\DIAL_Flow\Output
output_path = C:\DIAL_Flow\Lists
state_population_demographics = C:\DIAL_Flow\Data\state_demographics.csv

[Parameters]
contact_days_threshold = 30
recent_days_window = 1
target_total_records = 10000
create_dt_split = 0.7
```

### Secure Configuration Management

**Option 1: Local Configuration File**
```python
# Place config.ini in the same directory as the Python scripts
# Advantages: Simple deployment
# Considerations: Ensure proper file permissions (read-only for service account)
```

**Option 2: Network Share Configuration**
```python
# Place config.ini on secure network share
# Advantages: Centralized configuration management
# Requirements: Network share access permissions
```

**Option 3: Environment Variables**
```python
# Store sensitive data in environment variables
import os

username = os.environ.get('DIAL_FLOW_SF_USERNAME')
password = os.environ.get('DIAL_FLOW_SF_PASSWORD')
```

### Security Best Practices

1. **File Permissions:** Set config.ini to read-only for service account
2. **Credential Rotation:** Implement regular password rotation schedule
3. **Access Control:** Limit file system access to authorized personnel only
4. **Encryption:** Consider encrypting sensitive configuration data
5. **Audit Logging:** Log all configuration access and modifications

---

## Database Setup

### Required Database Objects

**1. Phone Cleanup Queue Table**
```sql
CREATE TABLE phone_cleanup_queue (
    [Date] DATE NOT NULL,
    [Procedure] NVARCHAR(50) NOT NULL,
    [Id_Type] NVARCHAR(20) NOT NULL,
    [Id] NVARCHAR(18) NOT NULL,
    [MatchingField] NVARCHAR(50),
    [PhoneNumber] NVARCHAR(20),
    [ProcessedFlag] BIT DEFAULT 0,
    [CreatedDateTime] DATETIME2 DEFAULT GETDATE()
);

CREATE INDEX IX_phone_cleanup_queue_date_procedure 
ON phone_cleanup_queue ([Date], [Procedure]);
```

**2. Area Code Mapping Table**
```sql
CREATE TABLE dim_area_code_to_state_mapping (
    [AREA_CODE] NCHAR(3) NOT NULL PRIMARY KEY,
    [ST_ABBRV] NCHAR(2) NOT NULL,
    [STATE_NAME] NVARCHAR(50),
    [CreatedDate] DATETIME2 DEFAULT GETDATE()
);

-- Sample data insert
INSERT INTO dim_area_code_to_state_mapping (AREA_CODE, ST_ABBRV, STATE_NAME)
VALUES 
    ('212', 'NY', 'New York'),
    ('213', 'CA', 'California'),
    ('214', 'TX', 'Texas');
```

**3. Required Database Permissions**
```sql
-- Grant necessary permissions to service account
GRANT SELECT, INSERT, UPDATE, DELETE ON phone_cleanup_queue TO [DIAL_FLOW_SERVICE_ACCOUNT];
GRANT SELECT ON dim_area_code_to_state_mapping TO [DIAL_FLOW_SERVICE_ACCOUNT];
```

---

## Salesforce Configuration

### Required Salesforce Permissions

**User Permissions:**
- API Enabled
- View All Data (or specific object permissions)
- Modify All Data (for testing environments)

**Object Permissions:**
- Account: Read access
- Task: Read access  
- Researched_Phone_Number__c: Read access
- Research_Request__c: Read access
- Address_History__c: Read access
- User: Read access

### Salesforce API Limits

**Daily API Limits:**
- Monitor daily API usage in Salesforce Setup
- Recommended: Minimum 50,000 API calls per day
- Consider API call optimization for large datasets

**Query Optimization:**
```python
# Use selective queries to minimize API usage
# Good: SELECT specific fields only
sf_query = "SELECT Id, Phone, AccountId FROM Account WHERE Database_Status__c = 'Active'"

# Avoid: SELECT * queries
# Bad: sf_query = "SELECT FIELDS(ALL) FROM Account"
```

---

## Scheduled Execution Setup

### Windows Task Scheduler

**1. Create Basic Task**
```xml
<!-- Save as DIAL_Flow_Task.xml -->
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>DIAL-Flow Automation Suite Daily Execution</Description>
    <Author>IT Department</Author>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2024-01-01T06:30:00</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>C:\DIAL_Flow\dial_flow_env\Scripts\python.exe</Command>
      <Arguments>C:\DIAL_Flow\utilities\dedupe_iq.py</Arguments>
      <WorkingDirectory>C:\DIAL_Flow\utilities</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
```

**2. Import Task**
```powershell
# Import the scheduled task
schtasks /create /xml "C:\DIAL_Flow\DIAL_Flow_Task.xml" /tn "DIAL-Flow Suite"

# Verify task creation
schtasks /query /tn "DIAL-Flow Suite"
```

### Linux Cron Jobs

**Edit crontab:**
```bash
crontab -e

# Add daily execution at 6:30 AM
30 6 * * * /home/dialflow/dial_flow_env/bin/python /home/dialflow/utilities/dedupe_iq.py
```

### Execution Sequence

**Recommended Daily Execution Order:**
1. **DeDupe IQ** (6:30 AM) - Data governance
2. **InfoFlow IQ** (7:00 AM) - Research prioritization  
3. **AutoFlush IQ** (7:30 AM) - Phone quality management
4. **List IQ** (8:00 AM) - Call list generation

**Sample Batch Script (Windows):**
```batch
@echo off
cd /d "C:\DIAL_Flow\utilities"

echo Starting DIAL-Flow Suite Execution...
echo %date% %time% - Starting DeDupe IQ

call C:\DIAL_Flow\dial_flow_env\Scripts\activate.bat
python dedupe_iq.py

if %errorlevel% neq 0 (
    echo ERROR: DeDupe IQ failed with exit code %errorlevel%
    exit /b %errorlevel%
)

echo %date% %time% - DeDupe IQ completed successfully
echo %date% %time% - Starting InfoFlow IQ

python infoflow_iq.py

if %errorlevel% neq 0 (
    echo ERROR: InfoFlow IQ failed with exit code %errorlevel%
    exit /b %errorlevel%
)

echo %date% %time% - InfoFlow IQ completed successfully
echo %date% %time% - Starting AutoFlush IQ

python autoflush_iq.py

if %errorlevel% neq 0 (
    echo ERROR: AutoFlush IQ failed with exit code %errorlevel%
    exit /b %errorlevel%
)

echo %date% %time% - AutoFlush IQ completed successfully
echo %date% %time% - Starting List IQ

python list_iq.py

if %errorlevel% neq 0 (
    echo ERROR: List IQ failed with exit code %errorlevel%
    exit /b %errorlevel%
)

echo %date% %time% - DIAL-Flow Suite execution completed successfully
```

---

## Monitoring & Maintenance

### Log File Management

**Log Rotation Configuration:**
```python
import logging
from logging.handlers import RotatingFileHandler

# Configure rotating log files (10MB max, keep 5 backups)
log_handler = RotatingFileHandler(
    'dial_flow.log', 
    maxBytes=10*1024*1024, 
    backupCount=5
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[log_handler, logging.StreamHandler()]
)
```

### Performance Monitoring

**Key Metrics to Monitor:**
- Execution time per utility
- Memory usage during processing
- Database connection health
- API call consumption
- Email delivery success rates

**Sample Monitoring Script:**
```python
import psutil
import time

def monitor_system_resources():
    """Monitor system resources during DIAL-Flow execution"""
    process = psutil.Process()
    
    print(f"CPU Usage: {psutil.cpu_percent()}%")
    print(f"Memory Usage: {process.memory_info().rss / 1024 / 1024:.2f} MB")
    print(f"Available Memory: {psutil.virtual_memory().available / 1024 / 1024:.2f} MB")
```

### Maintenance Tasks

**Weekly Maintenance:**
- Review log files for errors or warnings
- Monitor API usage and limits
- Verify email delivery and recipient lists
- Check database connection health

**Monthly Maintenance:**
- Rotate log files manually if needed
- Update configuration parameters based on performance
- Review and optimize SQL Server performance
- Validate Salesforce API permissions

**Quarterly Maintenance:**
- Update Python packages to latest compatible versions
- Review and update business rule parameters
- Conduct full system performance testing
- Update documentation with any configuration changes

---

## Troubleshooting Guide

### Common Issues and Solutions

**1. Salesforce Connection Failures**
```python
# Error: Authentication failure
# Solution: Verify username, password, and security token
# Check: https://help.salesforce.com/s/articleView?id=sf.user_security_token.htm

# Error: API limit exceeded
# Solution: Monitor API usage in Salesforce Setup > System Overview
```

**2. Database Connection Issues**
```python
# Error: [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]Login failed
# Solution: Verify database credentials and connection string
# Check: Network connectivity to SQL Server

# Error: Database timeout
# Solution: Optimize queries or increase timeout values
conn = pyodbc.connect(conn_str, timeout=60)
```

**3. Memory Issues**
```python
# Error: MemoryError during large dataset processing
# Solution: Reduce chunk_size parameter or increase system RAM
processor = MemoryOptimizedProcessor(chunk_size=2500)  # Reduce from 5000
```

**4. File Path Issues**
```python
# Error: FileNotFoundError for output paths
# Solution: Verify directory existence and permissions
if not os.path.exists(output_directory):
    os.makedirs(output_directory)
```

### Error Recovery Procedures

**Email Notification Failure Recovery:**
```python
def send_emergency_notification():
    """Send notification through alternative method if primary email fails"""
    try:
        # Primary email method
        send_email(subject, status, config)
    except Exception as e:
        # Alternative notification method
        log_critical_error(f"Email notification failed: {e}")
        # Could implement: SMS, Slack, or alternative email service
```

**Database Recovery Procedures:**
```python
def handle_database_failure():
    """Graceful handling of database connection failures"""
    try:
        # Primary database operation
        execute_sql_operation()
    except Exception as db_error:
        # Log error and continue with file-based backup
        logging.error(f"Database operation failed: {db_error}")
        save_to_backup_file()
```

---

## Security Considerations

### Access Control

**Service Account Configuration:**
- Create dedicated service account for DIAL-Flow execution
- Grant minimum required permissions only
- Implement password rotation schedule
- Monitor service account usage

**File System Security:**
- Set appropriate permissions on configuration files
- Encrypt sensitive configuration data if required
- Implement audit logging for file access
- Regular security assessment of deployment environment

### Network Security

**Firewall Configuration:**
- Allow outbound HTTPS (443) for Salesforce API
- Allow SMTP (587) for email notifications
- Allow SQL Server port (typically 1433) for database access
- Restrict inbound access to deployment server

**API Security:**
- Use least-privilege Salesforce user account
- Monitor API usage for unusual patterns
- Implement API rate limiting if necessary
- Regular review of API access logs

---

## Performance Optimization

### Hardware Optimization

**Memory Configuration:**
- Minimum 16GB RAM for production environments
- Consider SSD storage for improved I/O performance
- Multi-core CPU for parallel processing capabilities

**Network Optimization:**
- High-speed internet connection for API efficiency
- Local network file shares for configuration management
- Minimize network latency to database server

### Software Optimization

**Python Configuration:**
```python
# Optimize pandas for performance
import pandas as pd
pd.set_option('compute.use_bottleneck', True)
pd.set_option('compute.use_numexpr', True)

# Configure memory-efficient data types
df = df.astype({
    'phone_field': 'category',
    'numeric_field': 'int32'
})
```

**Database Optimization:**
```sql
-- Create appropriate indexes for performance
CREATE INDEX IX_account_status ON Account (Database_Status__c) INCLUDE (Id, Phone);
CREATE INDEX IX_task_disposition ON Task (CallDisposition, ActivityDate) INCLUDE (AccountId);
```

This deployment guide provides a comprehensive foundation for successfully implementing DIAL-Flow in production environments while maintaining security, performance, and reliability standards.
