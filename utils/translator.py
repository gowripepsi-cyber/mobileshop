import os
import json

TRANSLATIONS_FILE = os.path.join(os.path.dirname(__file__), "translations.json")

# Default comprehensive English -> Tamil dictionary
DEFAULT_TRANSLATIONS = {
    # Navigation & Core
    "Dashboard": "முகப்பு",
    "Master Records": "முதன்மை பதிவுகள்",
    "Purchase Entry": "கொள்முதல் பதிவு",
    "Sales Invoice": "விற்பனை பில்",
    "Service Cards": "சர்வீஸ் கார்டுகள்",
    "Payments": "வரவு செலவு",
    "Bank & Cash": "வங்கி & கல்லா",
    "Reports": "அறிக்கைகள்",
    "Settings": "அமைப்புகள்",
    "UPI / Money Transfer": "மணி டிரான்ஸ்பர்",
    "Log Out": "வெளியேறு",
    "Welcome": "வணக்கம்",
    "MANAGEMENT & REPORTS": "மேலாண்மை & அறிக்கைகள்",
    "FINANCE & HR": "நிதி & ஊழியர்கள்",
    "OPERATIONS & BILLING": "விற்பனை & கொள்முதல்",
    "MAIN": "முதன்மை",
    "Base Salary": "அடிப்படை சம்பளம்",
    "Technicians": "டெக்னீஷியன்கள்",
    "Active Staff": "செயலில் உள்ள ஊழியர்கள்",
    "Total Staff": "மொத்த ஊழியர்கள்",
    "This Month's Expenses": "இந்த மாத செலவு",
    "Today's Expenses": "இன்றைய செலவு",
    "Save Attendance": "வருகை சேமிக்குக",
    "Mark All Present": "அனைவரும் வருகை",
    "Record Expense": "செலவு பதிவு செய்க",
    "Pay Salary / Advance": "சம்பளம் / முன்பணம் வழங்குக",
    "Salary & Advances": "சம்பளம் & முன்பணம்",
    "Daily Attendance": "தினசரி வருகை",
    "Staff Directory": "ஊழியர்கள் பட்டியல்",
    "Expense Analytics": "செலவு பகுப்பாய்வு",
    "Expense Categories": "செலவு பிரிவுகள்",
    "Expense Register": "செலவு பதிவேடு",
    "Daily Expenses": "தினசரி செலவுகள்",
    "Staff Management": "ஊழியர்கள் மேலாண்மை",
    "Expenses": "செலவுகள்",

    # Headers & Titles
    "Inventory & Accounting": "சரக்கு & கணக்கு மேலாண்மை",
    "Purchase Entry (Inventory)": "கொள்முதல் பதிவு (சரக்கு)",
    "Repair Center Job Cards": "மொபைல் சர்வீஸ் கார்டுகள்",
    "Payments Ledger": "வரவு செலவு லெட்ஜர்",
    "Reports & Financial Analysis": "அறிக்கைகள் & நிதி பகுப்பாய்வு",
    "System Settings & Database Admin": "அமைப்புகள் & தரவுத்தள மேலாண்மை",
    "Shop Details": "கடை விவரங்கள்",
    "User Management": "பயனர் மேலாண்மை",
    "Change Password": "கடவுச்சொல் மாற்றம்",
    "Backup & Restore": "காப்பு & மீட்டமை",
    "License & Maintenance": "உரிமம் & பராமரிப்பு",
    "Language Dictionary": "மொழி அகராதி",
    "Bank Accounts & Cash Drawer Management": "வங்கி & கல்லா மேலாண்மை",

    # Cash Drawer & Banking
    "Cash Drawer": "கல்லாப்பெட்டி",
    "Cash in Hand": "கல்லா இருப்பு",
    "Today's Cash In": "இன்றைய வரவு",
    "Today's Cash Out": "இன்றைய செலவு",
    "Total Bank Balances": "மொத்த வங்கி இருப்பு",
    "Registered Bank Accounts": "பதிவு செய்யப்பட்ட வங்கிகள்",
    "Bank Accounts & Passbook": "வங்கிக் கணக்குகள் & பாஸ்புக்",
    "Bank Accounts Overview": "வங்கிக் கணக்குகள் விவரம்",
    "Bank Passbook Transactions": "வங்கி பாஸ்புக் பரிவர்த்தனைகள்",
    "Fund Transfer": "பணப் பரிமாற்றம்",
    "Execute Fund Transfer": "பணப் பரிமாற்றம் செய்க",
    "Recent Transfer History": "முந்தைய பரிமாற்றங்கள்",
    "Daily Expenses & Direct Income": "அன்றாட செலவுகள் & நேரடி வரவு",
    "Record Expense or Direct Income": "செலவு அல்லது நேரடி வரவு பதிவு",
    "Expenses & Direct Transactions Log": "செலவுகள் & வரவு பதிவேடு",

    # Actions & Buttons
    "Quick Cash In": "உடனடி ரொக்க வரவு",
    "Cash Expense": "கடை செலவு",
    "+ Quick Cash In": "+ உடனடி ரொக்க வரவு",
    "- Cash Expense": "- கடை செலவு",
    "+ Add Bank Account": "+ புதிய வங்கி சேர்க்க",
    "Edit Bank": "வங்கி திருத்து",
    "Complete Transfer": "பரிமாற்றத்தை முடி",
    "Save Entry": "பதிவை சேமி",
    "Save": "சேமி",
    "Cancel": "ரத்து",
    "Delete": "நீக்கு",
    "Edit": "திருத்து",
    "View": "பார்வையிடு",
    "Bill": "பில் போடு",
    "Search": "தேடுக",
    "Copy": "நகலெடு",
    "Print": "அச்சிடு",
    "Export": "ஏற்றுமதி",
    "New Job Card": "புதிய சர்வீஸ் கார்டு",

    # Forms, Types & Labels
    "Cash to Bank (Deposit)": "கல்லாவிலிருந்து வங்கிக்கு (டெபாசிட்)",
    "Bank to Cash (Withdrawal)": "வங்கியிலிருந்து கல்லாவிற்கு (எடுத்தல்)",
    "Bank to Bank Transfer": "வங்கியிலிருந்து வங்கிக்கு மாற்றம்",
    "Withdrawal / Expense": "கடை செலவு (வெளியே)",
    "Deposit / Income": "நேரடி வரவு (உள்ளே)",
    "Cash": "ரொக்கம்",
    "Bank": "வங்கி",
    "Amount": "தொகை",
    "Date": "தேதி",
    "Created Date": "உருவாக்கிய தேதி",
    "Customer": "வாடிக்கையாளர்",
    "Customer Name": "வாடிக்கையாளர் பெயர்",
    "Supplier": "சப்ளையர்",
    "Supplier Name": "சப்ளையர் பெயர்",
    "Mobile": "மொபைல் எண்",
    "Device Detail": "சாதன விவரம்",
    "Status": "நிலை",
    "Labor": "கூலி",
    "Total": "மொத்தம்",
    "Paid": "செலுத்தியது",
    "Balance": "நிலுவை",
    "Description": "விளக்கம்",
    "Remarks": "குறிப்பு",
    "From Account": "அனுப்பும் கணக்கு",
    "To Account": "பெறும் கணக்கு",
    "Account Type": "கணக்கு வகை",
    "Bank Name": "வங்கி பெயர்",
    "Account Number": "கணக்கு எண்",
    "Account Display Name": "காட்சி பெயர்",
    "Current Balance": "தற்போதைய இருப்பு",
    "Opening Balance": "துவக்க இருப்பு",
    "Filter Period": "கால அளவு",
    "All Transactions": "அனைத்து பரிவர்த்தனைகள்",
    "Today": "இன்று",
    "Yesterday": "நேற்று",
    "This Week": "இந்த வாரம்",
    "This Month": "இந்த மாதம்",
    "All Registered Banks": "அனைத்து வங்கிகள்",

    # Common Expense / Income Categories
    "Shop Rent": "கடை வாடகை",
    "Electricity Bill": "மின்சாரக் கட்டணம் (EB)",
    "Tea & Refreshments": "டீ & சிற்றுண்டி",
    "Staff Salary / Advance": "பணியாளர் சம்பளம் / முன்பணம்",
    "Stationery & Printing": "ஸ்டேஷனரி & பிரிண்டிங்",
    "Transportation & Courier": "கூரியர் & போக்குவரத்து",
    "Shop Maintenance / Repair": "கடை பராமரிப்பு",
    "Marketing & Promotion": "விளம்பரம்",
    "Capital Injection": "மூலதன வரவு",
    "Scrap / Old Parts Sale": "பழைய பொருட்கள் விற்பனை",
    "Commission Income": "கமிஷன் வருமானம்",
    "Misc Income / Expense": "இதர வரவு / செலவு"
}

_memory_translations = None
_current_language = None


def load_translations() -> dict:
    """Loads translations from translations.json, falling back to defaults."""
    global _memory_translations
    if _memory_translations is not None:
        return _memory_translations

    if os.path.exists(TRANSLATIONS_FILE):
        try:
            with open(TRANSLATIONS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                # Merge with defaults in case new keys were added
                merged = dict(DEFAULT_TRANSLATIONS)
                merged.update(loaded)
                _memory_translations = merged
                return _memory_translations
        except Exception as e:
            print(f"Error loading translations file: {e}")

    _memory_translations = dict(DEFAULT_TRANSLATIONS)
    save_translations(_memory_translations)
    return _memory_translations


def save_translations(translations_dict: dict) -> bool:
    """Saves the translations dictionary to translations.json."""
    global _memory_translations
    _memory_translations = dict(translations_dict)
    try:
        with open(TRANSLATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(_memory_translations, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving translations file: {e}")
        return False


def get_current_language() -> str:
    """Returns the current language code ('en' or 'ta'). Default is 'en'."""
    global _current_language
    if _current_language:
        return _current_language

    try:
        from database import Session, Setting
        session = Session()
        try:
            sett = session.query(Setting).filter_by(key='app_language').first()
            if sett and sett.value in ('en', 'ta'):
                _current_language = sett.value
                return _current_language
        finally:
            session.close()
    except Exception:
        pass

    _current_language = 'en'
    return _current_language


def set_current_language(lang_code: str):
    """Sets and persists current language ('en' or 'ta')."""
    global _current_language
    if lang_code not in ('en', 'ta'):
        lang_code = 'en'

    _current_language = lang_code

    try:
        from database import Session, Setting
        session = Session()
        try:
            sett = session.query(Setting).filter_by(key='app_language').first()
            if sett:
                sett.value = lang_code
            else:
                session.add(Setting(key='app_language', value=lang_code))
            session.commit()
        finally:
            session.close()
    except Exception as e:
        print(f"Could not persist language to DB: {e}")


def tr(text: str) -> str:
    """Translates text if current language is 'ta'. Returns original English if 'en' or not found."""
    if not text or not isinstance(text, str):
        return text

    if get_current_language() != 'ta':
        return text

    dict_map = load_translations()
    return dict_map.get(text, text)


def update_single_translation(english_key: str, tamil_val: str) -> bool:
    """Updates a single translation entry and saves it."""
    d = load_translations()
    d[english_key] = tamil_val
    return save_translations(d)


def delete_single_translation(english_key: str) -> bool:
    """Deletes a translation entry and saves."""
    d = load_translations()
    if english_key in d:
        del d[english_key]
        return save_translations(d)
    return False


def reset_to_defaults() -> bool:
    """Resets the dictionary back to factory defaults."""
    global _memory_translations
    _memory_translations = dict(DEFAULT_TRANSLATIONS)
    return save_translations(_memory_translations)

