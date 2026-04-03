import os
import re
import openpyxl
from datetime import datetime
from PyPDF2 import PdfReader

# ✅ FIXED: Safe import for liteparse
try:
    from liteparse import LiteParse
except ImportError:
    LiteParse = None


def extract_dates_from_text(text):
    """Find ISO or common dates in text and return the latest date."""
    date_patterns = [
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{2}/\d{2}/\d{4})",
        r"(\d{2}\.\d{2}\.\d{4})"
    ]
    dates = []

    for pat in date_patterns:
        for m in re.findall(pat, text):
            try:
                if '-' in m:
                    d = datetime.fromisoformat(m)
                elif '/' in m:
                    d = datetime.strptime(m, '%m/%d/%Y')
                else:
                    d = datetime.strptime(m, '%d.%m.%Y')
                dates.append(d)
            except Exception:
                continue

    return max(dates) if dates else None


def infer_source_type(file_path):
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.pdf':
        return 'policy'
    if ext in ['.xlsx', '.xls']:
        return 'table'
    if ext in ['.eml', '.txt']:
        return 'email'
    if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif']:
        return 'image'

    return 'unknown'


# ✅ FIXED: Safe initialization
if LiteParse is not None:
    try:
        liteparser = LiteParse(install_if_not_available=True)
    except Exception:
        liteparser = None
else:
    liteparser = None


def convert_pdf_to_markdown(file_path):
    """Convert PDF to Markdown using LiteParse if available, otherwise PyPDF2."""
    if liteparser is not None:
        try:
            parse_result = liteparser.parse(file_path, ocr_enabled=True)
            text = parse_result.text
            return f"# {os.path.basename(file_path)}\n\n{text}"
        except Exception:
            pass  # fallback

    # Fallback using PyPDF2
    with open(file_path, 'rb') as f:
        reader = PdfReader(f)
        text = ""

        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"

    return f"# {os.path.basename(file_path)}\n\n{text}"


def convert_excel_to_markdown(file_path):
    """Convert Excel to structured table data."""
    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active

    headers = [cell.value for cell in sheet[1]]
    rows = []

    for i, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
        row_data = {
            str(headers[j] if headers[j] else f"col{j}"): row[j]
            for j in range(len(headers))
        }
        rows.append({
            'row_index': i - 1,
            'values': row_data,
        })

    all_text = ' '.join(str(v) for row in rows for v in row['values'].values())

    return {
        'type': 'table',
        'headers': [str(h) for h in headers],
        'rows': rows,
        'source_name': os.path.basename(file_path),
        'file_date': extract_dates_from_text(all_text)
    }


def convert_image_to_markdown(file_path):
    """Convert image using LiteParse OCR or fallback to pytesseract."""
    if liteparser is not None:
        try:
            parse_result = liteparser.parse(file_path, ocr_enabled=True)
            return f"# {os.path.basename(file_path)}\n\n{parse_result.text}"
        except Exception:
            pass

    # Fallback to pytesseract
    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        raise RuntimeError(
            "Install dependencies: pip install Pillow pytesseract"
        )

    try:
        img = Image.open(file_path)
        text = pytesseract.image_to_string(img)
        return f"# {os.path.basename(file_path)}\n\n{text}"
    except Exception as e:
        raise RuntimeError(f"Image OCR failed: {e}")


def convert_email_to_markdown(file_path):
    """Convert email (.eml/.txt) to Markdown."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        raw = f.read()

    if '\n\n' in raw:
        headers, body = raw.split('\n\n', 1)
    else:
        headers, body = '', raw

    markdown = f"# {os.path.basename(file_path)}\n\n"
    markdown += "## Headers\n\n" + headers.strip() + "\n\n"
    markdown += "## Body\n\n" + body.strip() + "\n"

    return markdown


def ingest_file(file_path):
    """Main ingestion router."""
    ext = os.path.splitext(file_path)[1].lower()

    if ext == '.pdf':
        return convert_pdf_to_markdown(file_path)
    elif ext in ['.xlsx', '.xls']:
        return convert_excel_to_markdown(file_path)
    elif ext in ['.eml', '.txt']:
        return convert_email_to_markdown(file_path)
    elif ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.gif']:
        return convert_image_to_markdown(file_path)
    else:
        raise ValueError("Unsupported file type")