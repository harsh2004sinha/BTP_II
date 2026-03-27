import pdfplumber
import pandas as pd
import re
import os
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BillParser:
    """
    Service to parse electricity bills (PDF/image).
    Extracts monthly consumption data.
    """
    
    # Regex patterns for extraction
    PATTERNS = {
        'units': [
            r'(\d+\.?\d*)\s*(?:kWh|kwh|KWH|units?)',
            r'(?:consumption|usage|used)[:\s]+(\d+\.?\d*)',
            r'(?:total\s+)?(?:units?|kwh)[:\s]+(\d+\.?\d*)',
        ],
        'amount': [
            r'(?:total|amount|bill)[:\s]+(?:RM|MYR|\$|£|€)?\s*(\d+\.?\d*)',
            r'(?:RM|MYR|\$)\s*(\d+\.?\d*)',
        ],
        'date': [
            r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})',
            r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
            r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|'
            r'Dec(?:ember)?)[,\s]+(\d{4})',
        ]
    }
    
    MONTH_MAP = {
        'jan': 'January', 'feb': 'February', 'mar': 'March',
        'apr': 'April', 'may': 'May', 'jun': 'June',
        'jul': 'July', 'aug': 'August', 'sep': 'September',
        'oct': 'October', 'nov': 'November', 'dec': 'December'
    }
    
    @staticmethod
    def parse_pdf(file_path: str) -> List[Dict]:
        """
        Parse PDF electricity bill.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            List of consumption records
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        extracted_data = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                full_text = ""
                
                # Extract text from all pages
                for page_num, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        full_text += page_text + "\n"
                    
                    # Try to extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        table_data = BillParser._parse_table(table)
                        if table_data:
                            extracted_data.extend(table_data)
                
                # Parse text if no table data found
                if not extracted_data:
                    text_data = BillParser._parse_text(full_text)
                    if text_data:
                        extracted_data.append(text_data)
                        
        except Exception as e:
            logger.error(f"PDF parsing error: {str(e)}")
            raise ValueError(f"Could not parse PDF file: {str(e)}")
        
        if not extracted_data:
            raise ValueError(
                "Could not extract consumption data from bill. "
                "Please ensure the bill contains kWh usage information."
            )
        
        return extracted_data
    
    @staticmethod
    def _parse_table(table: list) -> List[Dict]:
        """Extract data from PDF table"""
        results = []
        
        if not table:
            return results
        
        for row in table:
            if not row:
                continue
            
            row_text = " ".join([str(cell) for cell in row if cell])
            
            # Look for rows containing kWh values
            if any(keyword in row_text.lower() 
                   for keyword in ['kwh', 'unit', 'consumption', 'usage']):
                
                data = BillParser._extract_from_text(row_text)
                if data and data.get('units'):
                    results.append(data)
        
        return results
    
    @staticmethod
    def _parse_text(text: str) -> Optional[Dict]:
        """Extract consumption data from raw text"""
        return BillParser._extract_from_text(text)
    
    @staticmethod
    def _extract_from_text(text: str) -> Dict:
        """
        Extract units, amount, and date from text using regex.
        """
        result = {}
        
        # Extract units (kWh)
        for pattern in BillParser.PATTERNS['units']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    result['units'] = float(match.group(1))
                    break
                except (ValueError, IndexError):
                    continue
        
        # Extract amount
        for pattern in BillParser.PATTERNS['amount']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    result['totalAmount'] = float(match.group(1))
                    break
                except (ValueError, IndexError):
                    continue
        
        # Extract date
        for pattern in BillParser.PATTERNS['date']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['date'] = match.group(0)
                
                # Try to extract month name
                month_match = re.search(
                    r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|'
                    r'Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|'
                    r'Nov(?:ember)?|Dec(?:ember)?)',
                    text, re.IGNORECASE
                )
                if month_match:
                    month_short = month_match.group(1)[:3].lower()
                    result['month'] = BillParser.MONTH_MAP.get(
                        month_short, 
                        month_match.group(1)
                    )
                
                # Try to extract year
                year_match = re.search(r'\b(20\d{2})\b', text)
                if year_match:
                    result['year'] = int(year_match.group(1))
                
                break
        
        return result
    
    @staticmethod
    def parse_csv(file_path: str) -> List[Dict]:
        """Parse CSV electricity bill data"""
        try:
            df = pd.read_csv(file_path)
            df.columns = df.columns.str.lower().str.strip()
            
            results = []
            
            for _, row in df.iterrows():
                record = {}
                
                # Map common column names
                column_mapping = {
                    'units': ['units', 'kwh', 'consumption', 'usage', 'energy'],
                    'date': ['date', 'period', 'month', 'billing_date'],
                    'amount': ['amount', 'total', 'bill_amount', 'cost']
                }
                
                for field, possible_cols in column_mapping.items():
                    for col in possible_cols:
                        if col in df.columns:
                            record[field] = row[col]
                            break
                
                if record.get('units'):
                    results.append(record)
            
            return results
            
        except Exception as e:
            raise ValueError(f"Could not parse CSV file: {str(e)}")
    
    @staticmethod
    def estimate_monthly_consumption(
        total_annual: float,
        pattern: str = "flat"
    ) -> List[Dict]:
        """
        Estimate monthly consumption from annual total.
        
        Args:
            total_annual: Total annual consumption in kWh
            pattern: Distribution pattern (flat/seasonal/custom)
        """
        months = [
            'January', 'February', 'March', 'April', 
            'May', 'June', 'July', 'August',
            'September', 'October', 'November', 'December'
        ]
        
        if pattern == "flat":
            monthly_avg = total_annual / 12
            weights = [1.0] * 12
        elif pattern == "seasonal":
            # Higher in summer/winter for cooling/heating
            weights = [1.1, 1.0, 0.9, 0.9, 1.0, 1.2, 1.3, 1.3, 1.1, 0.9, 0.9, 1.1]
        else:
            weights = [1.0] * 12
        
        total_weight = sum(weights)
        records = []
        
        for i, month in enumerate(months):
            units = (total_annual * weights[i]) / total_weight
            records.append({
                'month': month,
                'year': 2024,
                'units': round(units, 2),
                'date': f"2024-{i+1:02d}"
            })
        
        return records