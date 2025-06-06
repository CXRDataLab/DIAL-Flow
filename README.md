# DIAL-Flow Automation Suite

**Advanced Python automation system that increased contact rates by 36% (4.4% → 6.0%) through intelligent data processing, geographic optimization, and automated workflow management.**

## Overview

DIAL-Flow is a comprehensive four-utility automation suite designed to optimize outbound calling operations for a structured settlement company managing 400,000+ seller accounts and 1M+ call dispositions. The system eliminates manual data management processes while implementing intelligent prioritization and geographic segmentation logic.

## Business Impact

- **36% increase in contact rates** (4.4% to 6.0%)
- **Eliminated duplicate calling** across 400,000 seller accounts
- **Automated research prioritization** reducing manual man-hours
- **Intelligent phone number management** with threshold-based quality controls
- **Dynamic list generation** with census-based geographic segmentation

## System Architecture

DIAL-Flow integrates multiple data sources through four specialized utilities:

### 🔍 **DeDupe IQ**
- **Purpose:** Identifies and eliminates duplicate records
- **Problem Solved:** Multiple database entries causing duplicate calls and split account management
- **Data Sources:** Salesforce CRM
- **Output:** CSV of records requiring removal

### 📊 **InfoFlow IQ** 
- **Purpose:** Automates research request generation and prioritization
- **Problem Solved:** Manual skip tracing prioritization consuming excessive man-hours
- **Schedule:** Bi-weekly (Mondays & Wednesdays)
- **Data Sources:** Salesforce CRM

### 🚿 **AutoFlush IQ**
- **Purpose:** Removes unverified phone numbers based on disposition thresholds
- **Problem Solved:** Manual phone number cleanup and quality control
- **Schedule:** Daily automated execution
- **Logic:** Configurable disposition rules (e.g., "wrong number" × 3 attempts)

### 📋 **List IQ**
- **Purpose:** Generates optimized daily call lists with geographic segmentation
- **Problem Solved:** Static lists ordered only by last disposition date
- **Method:** Census-based population percentage distribution
- **Schedule:** Daily list generation

## Technical Stack

- **Language:** Python 3.x
- **Database Integration:** SQL Server, Salesforce CRM
- **Key Libraries:** pandas, simple_salesforce, pyodbc, smtplib, configparser
- **Deployment:** Automated scheduling with email notifications

## Repository Structure
DIAL-Flow/
├── utilities/          # Core Python automation utilities
├── documentation/      # Technical specifications and process flows
└── README.md          # Project overview (this file)

---

*This automation suite demonstrates advanced data engineering, business process optimization, and measurable ROI through intelligent automation design.*
