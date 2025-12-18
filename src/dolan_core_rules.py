# dolan_core_rules.py
DOLAN_RULES = {
    "business_core": {
        "required_courses": [
            "ACCT1011","ACCT1012","AETH2291","BUSN1101",
            "BUSN3211","DATA1101","DATA1101L","FNCE2101",
            "INTL2101","MGMT2101","MGMT4300","MKTG1101"
        ],
        "co_reqs": {"DATA1101": ["DATA1101L"]},
        "notes":  {"MGMT4300": "Capstone (senior)", "DATA1101L": "0-credit lab with DATA1101"}
    }
}
