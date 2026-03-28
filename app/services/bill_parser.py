import fitz
import PyPDF2
import pandas as pd
import re
import os
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class BillParser:
    """
    Service to parse electricity bills (PDF / CSV).
    """

    MONTH_MAP = {
        'jan': 'January',  'feb': 'February', 'mar': 'March',
        'apr': 'April',    'may': 'May',       'jun': 'June',
        'jul': 'July',     'aug': 'August',    'sep': 'September',
        'oct': 'October',  'nov': 'November',  'dec': 'December',
        '1':   'January',  '2':  'February',   '3':  'March',
        '4':   'April',    '5':  'May',         '6':  'June',
        '7':   'July',     '8':  'August',      '9':  'September',
        '10':  'October',  '11': 'November',   '12': 'December'
    }

    # ──────────────────────────────────────────────────────────
    #  CSV PARSER  (main fix)
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def parse_csv(file_path: str) -> List[Dict]:
        """
        Parse CSV electricity bill.
        Handles flexible column names automatically.
        """
        try:
            # ── Read file ──────────────────────────────────────
            df = pd.read_csv(file_path)

            logger.info(f"CSV loaded. Shape: {df.shape}")
            logger.info(f"Columns found: {list(df.columns)}")

            if df.empty:
                raise ValueError("CSV file is empty")

            # ── Clean column names ─────────────────────────────
            # Remove spaces, brackets, lowercase everything
            original_columns = list(df.columns)
            df.columns = (
                df.columns
                .str.strip()
                .str.lower()
                .str.replace(r'[\s\(\)\/\-]+', '_', regex=True)
                .str.replace(r'_+', '_', regex=True)
                .str.strip('_')
            )

            logger.info(f"Cleaned columns: {list(df.columns)}")

            # ── Find units column ──────────────────────────────
            units_col = BillParser._find_column(df, [
                'units_kwh', 'units', 'kwh', 'consumption',
                'usage', 'energy', 'unit', 'kw_h',
                'units_kw_h', 'electricity', 'reading'
            ])

            if units_col is None:
                # Try partial match
                for col in df.columns:
                    if any(k in col for k in ['unit', 'kwh', 'kw', 'consum', 'energy']):
                        units_col = col
                        break

            if units_col is None:
                logger.error(f"No units column found in: {list(df.columns)}")
                raise ValueError(
                    f"Could not find units/kWh column. "
                    f"Found columns: {original_columns}. "
                    f"Please ensure CSV has a column named "
                    f"'units', 'kWh', 'consumption' or similar."
                )

            logger.info(f"Using units column: '{units_col}'")

            # ── Find other columns ─────────────────────────────
            date_col = BillParser._find_column(df, [
                'date', 'period', 'billing_date', 'bill_date',
                'month_date', 'time', 'billing_period'
            ])

            month_col = BillParser._find_column(df, [
                'month', 'month_name', 'billing_month', 'mon'
            ])

            year_col = BillParser._find_column(df, [
                'year', 'yr', 'billing_year'
            ])

            amount_col = BillParser._find_column(df, [
                'amount', 'total', 'bill_amount', 'cost',
                'total_amount', 'charges', 'bill', 'price',
                'total_bill', 'payment'
            ])

            logger.info(
                f"Column mapping → "
                f"units='{units_col}' "
                f"date='{date_col}' "
                f"month='{month_col}' "
                f"year='{year_col}' "
                f"amount='{amount_col}'"
            )

            # ── Build records ──────────────────────────────────
            results = []

            for idx, row in df.iterrows():
                try:
                    # Get units value
                    raw_units = row[units_col]

                    # Skip empty rows
                    if pd.isna(raw_units) or str(raw_units).strip() == '':
                        continue

                    units = float(str(raw_units).replace(',', '').strip())

                    if units <= 0:
                        continue

                    # Get month
                    month = None
                    if month_col and not pd.isna(row[month_col]):
                        month_val = str(row[month_col]).strip()
                        month = BillParser._normalize_month(month_val)

                    # Get year
                    year = None
                    if year_col and not pd.isna(row[year_col]):
                        try:
                            year = int(float(str(row[year_col]).strip()))
                        except (ValueError, TypeError):
                            pass

                    # Get date
                    date_str = None
                    if date_col and not pd.isna(row[date_col]):
                        date_str = str(row[date_col]).strip()
                    elif year and month:
                        month_num = BillParser._month_to_num(month)
                        date_str  = f"{year}-{month_num:02d}"

                    # Get amount
                    total_amount = None
                    if amount_col and not pd.isna(row[amount_col]):
                        try:
                            total_amount = float(
                                str(row[amount_col])
                                .replace(',', '')
                                .replace('RM', '')
                                .replace('$', '')
                                .strip()
                            )
                        except (ValueError, TypeError):
                            pass

                    record = {
                        'units':       units,
                        'month':       month,
                        'year':        year,
                        'date':        date_str,
                        'totalAmount': total_amount
                    }

                    results.append(record)
                    logger.info(f"Row {idx}: parsed → {record}")

                except Exception as row_error:
                    logger.warning(f"Row {idx} skipped: {row_error}")
                    continue

            if not results:
                raise ValueError(
                    "CSV was read but no valid data rows found. "
                    "Please check your CSV has numeric values in the units column."
                )

            logger.info(f"CSV parsing complete. {len(results)} records found.")
            return results

        except ValueError:
            raise
        except Exception as e:
            logger.error(f"CSV parse error: {e}")
            raise ValueError(f"Could not parse CSV: {str(e)}")

    # ──────────────────────────────────────────────────────────
    #  HELPER: Find column by possible names
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _find_column(df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
        """Find first matching column name from list."""
        for name in possible_names:
            if name in df.columns:
                return name
        return None

    # ──────────────────────────────────────────────────────────
    #  HELPER: Normalize month value
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_month(value: str) -> Optional[str]:
        """Convert month value to full name."""
        if not value:
            return None

        value = str(value).strip()

        # Check if it's a number
        try:
            month_num = int(float(value))
            return BillParser.MONTH_MAP.get(str(month_num))
        except ValueError:
            pass

        # Check short name (Jan, Feb etc)
        short = value[:3].lower()
        if short in BillParser.MONTH_MAP:
            return BillParser.MONTH_MAP[short]

        # Check full name
        full = value.lower()
        for key, full_name in BillParser.MONTH_MAP.items():
            if full_name.lower() == full:
                return full_name

        return value  # Return as-is if no match

    # ──────────────────────────────────────────────────────────
    #  HELPER: Month name to number
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def _month_to_num(month_name: str) -> int:
        """Convert month name to number."""
        months = [
            'January', 'February', 'March', 'April',
            'May', 'June', 'July', 'August',
            'September', 'October', 'November', 'December'
        ]
        try:
            return months.index(month_name) + 1
        except ValueError:
            return 1

    # ──────────────────────────────────────────────────────────
    #  PDF PARSER
    # ──────────────────────────────────────────────────────────

    PATTERNS = {
        'units': [
            r'(\d+\.?\d*)\s*(?:kWh|kwh|KWH|units?)',
            r'(?:consumption|usage|used)[:\s]+(\d+\.?\d*)',
            r'(?:total\s+)?(?:units?|kwh)[:\s]+(\d+\.?\d*)',
        ],
        'amount': [
            r'(?:total|amount|bill)[:\s]+(?:RM|MYR|\$|£|€)?\s*(\d+\.?\d*)',
            r'(?:RM|MYR|\$)\s*(\d+\.?\d*)',
        ]
    }

    @staticmethod
    def parse_pdf(file_path: str) -> List[Dict]:
        """Parse PDF electricity bill using PyMuPDF."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        full_text = ""

        # Method 1: PyMuPDF
        try:
            doc = fitz.open(file_path)
            for page in doc:
                full_text += page.get_text() + "\n"
            doc.close()
            logger.info("PDF text extracted via PyMuPDF")

        except Exception as e:
            logger.warning(f"PyMuPDF failed: {e}. Trying PyPDF2...")

            # Method 2: PyPDF2 fallback
            try:
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        full_text += page.extract_text() + "\n"
            except Exception as e2:
                raise ValueError(f"Could not read PDF: {e2}")

        extracted_data = []

        if full_text.strip():
            multi = BillParser._extract_multi_month(full_text)
            if multi:
                extracted_data.extend(multi)
            else:
                single = BillParser._extract_from_text(full_text)
                if single and single.get('units'):
                    extracted_data.append(single)

        if not extracted_data:
            raise ValueError(
                "Could not extract data from PDF. "
                "Please ensure bill contains kWh information."
            )

        return extracted_data

    @staticmethod
    def _extract_multi_month(text: str) -> List[Dict]:
        """Extract multiple monthly records from text."""
        results = []
        row_pattern = re.compile(
            r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
            r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|'
            r'Dec(?:ember)?)[,.\s]+(\d{4})[^\d]*(\d+\.?\d*)\s*(?:kWh|kwh|units?)?',
            re.IGNORECASE
        )
        for match in row_pattern.finditer(text):
            month_raw = match.group(1)[:3].lower()
            year      = int(match.group(2))
            units     = float(match.group(3))
            month_full = BillParser.MONTH_MAP.get(month_raw, month_raw.capitalize())
            results.append({
                'month': month_full,
                'year':  year,
                'units': units,
                'date':  f"{year}-{BillParser._month_to_num(month_full):02d}"
            })
        return results

    @staticmethod
    def _extract_from_text(text: str) -> Dict:
        """Extract single record from raw text."""
        result = {}

        for pattern in BillParser.PATTERNS['units']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    result['units'] = float(match.group(1))
                    break
                except (ValueError, IndexError):
                    continue

        for pattern in BillParser.PATTERNS['amount']:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    result['totalAmount'] = float(match.group(1))
                    break
                except (ValueError, IndexError):
                    continue

        month_match = re.search(
            r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
            r'Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|'
            r'Dec(?:ember)?)',
            text, re.IGNORECASE
        )
        if month_match:
            short = month_match.group(1)[:3].lower()
            result['month'] = BillParser.MONTH_MAP.get(short, month_match.group(1))

        year_match = re.search(r'\b(20\d{2})\b', text)
        if year_match:
            result['year'] = int(year_match.group(1))

        return result

    # ──────────────────────────────────────────────────────────
    #  ESTIMATE HELPER
    # ──────────────────────────────────────────────────────────

    @staticmethod
    def estimate_monthly_consumption(
        total_annual: float,
        pattern: str = "flat"
    ) -> List[Dict]:
        """Distribute annual consumption into monthly estimates."""
        months = [
            'January',  'February', 'March',    'April',
            'May',      'June',     'July',      'August',
            'September','October',  'November',  'December'
        ]
        weights = (
            [1.1,1.0,0.9,0.9,1.0,1.2,1.3,1.3,1.1,0.9,0.9,1.1]
            if pattern == "seasonal"
            else [1.0] * 12
        )
        total_weight = sum(weights)
        return [
            {
                'month': month,
                'year':  2024,
                'units': round((total_annual * weights[i]) / total_weight, 2),
                'date':  f"2024-{i+1:02d}"
            }
            for i, month in enumerate(months)
        ]