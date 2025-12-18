# magis_core_rules.py
MAGIS_RULES = {
    # Tier I — Orientation
    "orientation": {
        "English":              {"need": 1, "by_course": ["ENGL1001"], "by_prefix": []},
        "History":              {"need": 1, "by_course": [], "by_prefix": ["HIST"], "level": "1000"},
        "Mathematics (Calc)":   {"need": 1, "by_course": ["MATH1121","MATH1122","MATH1141","MATH1142","MATH1171","MATH1172"]},
        "Statistics I":         {"need": 1, "by_course": ["MATH2217"]},
        "Language":             {"need": 1, "by_course": [], "by_prefix": ["SPAN","FREN","ITAL","GERM","CHIN","LATN","GRK"]},
        "Philosophy":           {"need": 1, "by_course": ["PHIL1101"]},
        "Religious Studies":    {"need": 1, "by_course": [], "by_prefix": ["RLST","RELI"], "level": "1000"}
    },
    # Tier II — Exploration
    "exploration": {
        "Behavioral & Social Sciences": {"need": 2, "by_course": ["ECON1011","ECON1012"]},
        "H/P/R 2000/3000":              {"need": 2, "by_course": [], "by_prefix": ["HIST","PHIL","RELI","RLST"], "level": "2000+"},
        "Literature":                   {"need": 1, "by_course": [], "by_prefix": ["ENGL","CLAS","MLL"]},
        "Natural Sciences":             {"need": 2, "by_course": ["ANTH1200","ANTH1210","PSYC2610"], "by_prefix": ["BIOL","CHEM","PHYS","ENVS"]},
        "Visual & Performing Arts":     {"need": 1, "by_course": [], "by_prefix": ["ART","MUSC","THEA","FILM","FTMA"], "level": "1000"}
    }
}
