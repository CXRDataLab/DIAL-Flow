# DIAL-Flow Utilities

This folder contains the four core Python utilities that comprise the DIAL-Flow automation suite. Each utility solves a specific operational challenge in outbound calling operations through advanced data processing and intelligent automation.

---

## 🔍 DeDupe IQ (`dedupe_iq.py`)

**Purpose:** Data Governance & Duplicate Detection Engine

**Problem Solved:** Eliminates duplicate records causing redundant outbound calls and split account management issues.

**Key Features:**
- Advanced temporal duplicate detection algorithm
- Preserves most recent records while flagging older duplicates for removal
- Processes 400,000+ account records in under 2 minutes
- Comprehensive audit trail with detailed logging

**Business Impact:**
- Eliminated duplicate calling across entire account database
- Prevented account executives from unknowingly managing duplicate accounts
- Improved customer experience by reducing excessive contact attempts

**Technical Highlights:**
- Sophisticated pandas grouping and temporal sorting
- Memory-optimized data processing
- Enterprise-grade error handling and email notifications

---

## 📊 InfoFlow IQ (`infoflow_iq.py`)

**Purpose:** Research Prioritization & Automation Engine

**Problem Solved:** Automates research request generation and prioritizes accounts requiring phone number research to optimize manual effort and costs.

**Key Features:**
- Multi-criteria filtering with complex business rule logic
- 90-day research frequency management to prevent duplicate efforts
- Memory-efficient chunked processing for large datasets
- Automated email delivery with CSV attachments for research teams

**Algorithm Sophistication:**
- Complex multi-table joins across Salesforce objects
- Intelligent phone field analysis (evaluates 6 different phone fields)
- Time-based filtering with configurable thresholds
- Geographic data enhancement with address history integration

**Business Impact:**
- Prioritized research requests reducing manual man-hours
- Systematic 90-day frequency enforcement preventing duplicate research
- Cost optimization through intelligent account prioritization

**Technical Highlights:**
- Advanced Salesforce API integration with chunked query processing
- Complex DataFrame operations and multi-criteria filtering
- Enterprise email automation with attachment capabilities

---

## 🚿 AutoFlush IQ (`autoflush_iq.py`)

**Purpose:** Phone Number Quality Management Engine

**Problem Solved:** Intelligent removal of problematic phone numbers based on call disposition patterns, improving overall calling efficiency and data quality.

**Key Features:**
- Dual threshold system: frequency-based + time-based analysis
- Parallel processing for high-performance phone field matching
- Advanced memory optimization for processing 1M+ call records
- Real-time system resource monitoring

**Algorithm Design:**
```python
# Threshold Logic
WRONG_NUMBER_THRESHOLD = 2      # Remove after 2+ wrong number attempts
DISCONNECTED_THRESHOLD = 3      # Remove after 3+ disconnected calls
TIME_SPAN_MINIMUM = 90          # Require 90+ days between first/last attempt
```

**Advanced Features:**
- **Memory Optimization Class:** Intelligent dtype selection reducing memory usage by 60%
- **Parallel Processing:** ThreadPoolExecutor improving processing speed by 3x
- **Vectorized Operations:** High-performance pandas/numpy computations
- **Performance Monitoring:** Real-time memory and CPU tracking with psutil

**Business Impact:**
- Automated phone number lifecycle management
- Improved calling efficiency through quality data maintenance
- Reduced agent frustration from calling bad numbers

**Technical Highlights:**
- Most sophisticated utility showcasing senior-level Python engineering
- Advanced concurrency programming with parallel execution
- Production-ready memory management and performance optimization

---

## 📋 List IQ (`list_iq.py`)

**Purpose:** Geographic Call List Optimization Engine

**Problem Solved:** Generates balanced daily call lists using census-based geographic distribution and temporal prioritization to maximize outbound calling effectiveness.

**Key Features:**
- Census-based population distribution for geographic optimization
- Mixed temporal selection algorithm (recent vs. historical record balancing)
- Area code to state mapping for intelligent geographic resolution
- Configurable target volumes with overflow handling

**Geographic Intelligence:**
```python
# Population-Weighted Distribution
target_per_state = (state_population_percentage / total_population) * target_total_records

# Mixed Temporal Selection  
recent_records = 70%    # Prioritize recent high-value leads
historical_records = 30%  # Include diverse historical data
```

**Algorithm Sophistication:**
- **Census Data Integration:** Uses actual population demographics for proportional representation
- **Temporal Prioritization:** Recent records (last 24-48 hours) receive highest priority
- **Intelligent Overflow Handling:** Maintains target list size through smart duplication
- **Quality Randomization:** Final randomization prevents systematic bias

**Business Impact:**
- Geographic balance ensuring proportional state representation
- Temporal optimization prioritizing recent high-value leads
- Improved contact rates through intelligent list composition

**Technical Highlights:**
- Advanced statistical analysis and population weighting
- Complex temporal analysis with configurable time windows
- Geographic intelligence with area code resolution

---

## 🏗️ System Integration

### Data Sources
- **Salesforce CRM:** Account, Task, User, and custom object data
- **SQL Server:** Area code mappings and census demographic data
- **File System:** CSV exports and configuration management

### Output Formats
- **CSV Files:** Formatted for dialer system consumption
- **SQL Tables:** Automated cleanup instructions for batch processing
- **Email Notifications:** Comprehensive status reports with attachments

### Technology Stack
```python
# Core Technologies
Python 3.x
pandas >= 1.5.3
simple_salesforce >= 1.12.2
pyodbc >= 4.0.35
numpy >= 1.24.3

# Advanced Features
concurrent.futures    # Parallel processing
psutil               # System monitoring
configparser         # Secure configuration
smtplib             # Email automation
```

---

## 📈 Performance Characteristics

| Utility | Dataset Size | Processing Time | Memory Usage | Key Optimization |
|---------|-------------|----------------|--------------|------------------|
| **DeDupe IQ** | 400K+ records | <2 minutes | <500MB | Temporal grouping & pandas optimization |
| **InfoFlow IQ** | 400K+ accounts | <5 minutes | <1GB | Chunked processing & memory management |
| **AutoFlush IQ** | 1M+ call records | <10 minutes | <2GB | Parallel processing & vectorized operations |
| **List IQ** | 400K+ records | <3 minutes | <800MB | Geographic algorithms & statistical analysis |

---

## 🔧 Configuration & Deployment

All utilities use a shared `config.ini` file for:
- **Salesforce API credentials** and connection settings
- **Database connection** parameters and authentication
- **Email notification** configuration and recipient management
- **Business rule parameters** and threshold settings
- **File paths** and output directory configurations

### Sample Configuration Structure
```ini
[Salesforce]
username = your_sf_username
password = your_sf_password
security_token = your_sf_token

[Database]
server = your_sql_server
database = your_database

[Email]
smtp_server = smtp.company.com
recipients = team@company.com

[Parameters]
contact_days_threshold = 30
target_total_records = 10000
```

---

## 🎯 Business Value Summary

### Measurable Results
- **36% increase in contact rates** (4.4% → 6.0%)
- **End-to-end automation** of previously manual processes
- **Cost optimization** through intelligent research prioritization
- **Quality improvement** via systematic data governance

### Technical Excellence
- **Enterprise-grade Python engineering** with advanced optimization
- **Production-ready architecture** with comprehensive error handling
- **Scalable design** supporting 400K+ accounts and 1M+ call records
- **Professional documentation** with complete deployment guides

### Skills Demonstrated
- **Advanced Data Engineering:** Large dataset processing with memory optimization
- **Algorithm Design:** Custom solutions for complex business problems  
- **System Integration:** Multi-platform automation (Salesforce, SQL Server, Email)
- **Production Operations:** Scheduled automation with monitoring and alerting

---

Each utility demonstrates sophisticated Python engineering skills while solving real business problems with measurable impact. The combination of advanced algorithms, performance optimization, and enterprise integration showcases senior-level development capabilities.
