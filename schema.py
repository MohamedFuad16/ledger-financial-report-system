# Standard 27-row Asset Schema for LLM Prompting
# IMPORTANT: This schema is passed directly to the LLM during prompt construction.
# It must NEVER contain ground-truth answers or answer keys!
ASSET_SCHEMA = [
    {
        "classification": "Current Assets",
        "subclassification": "",
        "item": "Current Assets",
        "description": "Quick Assets + Inventories, Net + Other Current Assets",
    },
    {
        "classification": "Current Assets",
        "subclassification": "Quick Assets",
        "item": "Quick Assets",
        "description": "Cash & Cash Equivalents + Accounts Receivable - Trade + Other Quick Assets",
    },
    {
        "classification": "Current Assets",
        "subclassification": "Quick Assets",
        "item": "Cash & Cash Equivalents",
        "description": "Cash and assets immediately convertible to cash.",
    },
    {
        "classification": "Current Assets",
        "subclassification": "Quick Assets",
        "item": "Accounts Receivable - Trade",
        "description": "Trade receivables arising from sales to customers.",
    },
    {
        "classification": "Current Assets",
        "subclassification": "Quick Assets",
        "item": "Other Quick Assets",
        "description": "Other short-term liquid assets that belong in Quick Assets.",
    },
    {
        "classification": "Current Assets",
        "subclassification": "",
        "item": "Inventories, Net",
        "description": "Inventory held for sale or use in production, net of applicable allowances.",
    },
    {
        "classification": "Current Assets",
        "subclassification": "Other Current Assets",
        "item": "Other Current Assets (subtotal)",
        "description": "Marketable Securities + Short-term Loan + Advance Payments + Other Current Assets",
    },
    {
        "classification": "Current Assets",
        "subclassification": "Other Current Assets",
        "item": "Marketable Securities",
        "description": "Current marketable or tradable securities.",
    },
    {
        "classification": "Current Assets",
        "subclassification": "Other Current Assets",
        "item": "Short-term Loan",
        "description": "Loan receivable expected to be collected within one year.",
    },
    {
        "classification": "Current Assets",
        "subclassification": "Other Current Assets",
        "item": "Advance Payments",
        "description": "Amounts paid in advance that are classified as current assets.",
    },
    {
        "classification": "Current Assets",
        "subclassification": "Other Current Assets",
        "item": "Other Current Assets",
        "description": "Other current assets not classified in the preceding requested fields.",
    },
    {
        "classification": "Fixed Assets",
        "subclassification": "",
        "item": "Fixed Assets",
        "description": "Tangible Assets + Intangible Assets + Financial Assets + Other Fixed Assets",
    },
    {
        "classification": "Fixed Assets",
        "subclassification": "Tangible Assets",
        "item": "Tangible Assets",
        "description": "Land + Buildings + Plant & Machinery + Construction in Progress + Other Equipment + Accumulated Depreciation",
    },
    {
        "classification": "Fixed Assets",
        "subclassification": "Tangible Assets",
        "item": "Land",
        "description": "Owned land classified as tangible fixed assets.",
    },
    {
        "classification": "Fixed Assets",
        "subclassification": "Tangible Assets",
        "item": "Buildings",
        "description": "Buildings such as offices, factories and warehouses.",
    },
    {
        "classification": "Fixed Assets",
        "subclassification": "Tangible Assets",
        "item": "Plant & Machinery",
        "description": "Production and operating plant and machinery.",
    },
    {
        "classification": "Fixed Assets",
        "subclassification": "Tangible Assets",
        "item": "Construction in Progress",
        "description": "Tangible assets under construction.",
    },
    {
        "classification": "Fixed Assets",
        "subclassification": "Tangible Assets",
        "item": "Other Equipment",
        "description": "Other equipment and fixtures classified as tangible fixed assets.",
    },
    {
        "classification": "Fixed Assets",
        "subclassification": "Tangible Assets",
        "item": "Accumulated Depreciation",
        "description": "Cumulative depreciation deducted from tangible assets. Preserve the negative sign.",
    },
    {
        "classification": "Fixed Assets",
        "subclassification": "",
        "item": "Intangible Assets",
        "description": "Non-physical long-lived assets.",
    },
    {
        "classification": "Fixed Assets",
        "subclassification": "Financial Assets",
        "item": "Financial Assets",
        "description": "Investments + Long-term Loan + Other Financial Assets",
    },
    {
        "classification": "Fixed Assets",
        "subclassification": "Financial Assets",
        "item": "Investments",
        "description": "Long-term investments classified as financial assets.",
    },
    {
        "classification": "Fixed Assets",
        "subclassification": "Financial Assets",
        "item": "Long-term Loan",
        "description": "Loan receivable expected to be collected after one year.",
    },
    {
        "classification": "Fixed Assets",
        "subclassification": "Financial Assets",
        "item": "Other Financial Assets",
        "description": "Other long-term financial assets not classified above.",
    },
    {
        "classification": "Fixed Assets",
        "subclassification": "",
        "item": "Other Fixed Assets",
        "description": "Other long-lived assets not classified in tangible, intangible or financial assets.",
    },
    {
        "classification": "Deferred Charges",
        "subclassification": "",
        "item": "Deferred Charges",
        "description": "Deferred costs recognized across accounting periods.",
    },
    {
        "classification": "Total Assets",
        "subclassification": "",
        "item": "Total Assets",
        "description": "Current Assets + Fixed Assets + Deferred Charges",
    },
]

# The arithmetic identities the schema implies. Every one of these must hold in
# a correct answer, and they hold *without needing an answer key* - which makes
# them the only quality signal available for a company we have no golden data
# for. Used by reconcile.py and by the test suite.
SUBTOTAL_IDENTITIES: list[tuple[str, list[str]]] = [
    ("Quick Assets", ["Cash & Cash Equivalents", "Accounts Receivable - Trade", "Other Quick Assets"]),
    ("Other Current Assets (subtotal)", ["Marketable Securities", "Short-term Loan", "Advance Payments", "Other Current Assets"]),
    ("Current Assets", ["Quick Assets", "Inventories, Net", "Other Current Assets (subtotal)"]),
    ("Tangible Assets", ["Land", "Buildings", "Plant & Machinery", "Construction in Progress", "Other Equipment", "Accumulated Depreciation"]),
    ("Financial Assets", ["Investments", "Long-term Loan", "Other Financial Assets"]),
    ("Fixed Assets", ["Tangible Assets", "Intangible Assets", "Financial Assets", "Other Fixed Assets"]),
    ("Total Assets", ["Current Assets", "Fixed Assets", "Deferred Charges"]),
]

# Multi-year benchmark answer-key store.
#
# FY2022 is the 27-row answer key supplied by the assignment problem statement.
# The other years are project-derived benchmark keys: arithmetic tests establish
# internal consistency, not source-level truth.  They must remain subject to a
# page-cited manual audit before research claims call them authoritative gold.
# Used strictly for post-extraction evaluation and UI comparison; these values
# are never included in model prompts.
GOLDEN_ANSWERS_STORE = {
    "2020": {
        "Current Assets": 14982,
        "Quick Assets": 9339,
        "Cash & Cash Equivalents": 4634,
        "Accounts Receivable - Trade": 4705,
        "Other Quick Assets": 0,
        "Inventories, Net": 4239,
        "Other Current Assets (subtotal)": 1404,
        "Marketable Securities": 404,
        "Short-term Loan": 0,
        "Advance Payments": 0,
        "Other Current Assets": 1000,
        "Fixed Assets": 32362,
        "Tangible Assets": 10285,
        "Land": 338,
        "Buildings": 8021,
        "Plant & Machinery": 16866,
        "Construction in Progress": 1425,
        "Other Equipment": 864,
        "Accumulated Depreciation": -17229,
        "Intangible Assets": 19637,
        "Financial Assets": 1151,
        "Investments": 214,
        "Long-term Loan": 0,
        "Other Financial Assets": 937,
        "Other Fixed Assets": 1289,
        "Deferred Charges": 0,
        "Total Assets": 47344
    },
    "2021": {
        "Current Assets": 15403,
        "Quick Assets": 9224,
        "Cash & Cash Equivalents": 4564,
        "Accounts Receivable - Trade": 4660,
        "Other Quick Assets": 0,
        "Inventories, Net": 4985,
        "Other Current Assets (subtotal)": 1194,
        "Marketable Securities": 201,
        "Short-term Loan": 0,
        "Advance Payments": 0,
        "Other Current Assets": 993,
        "Fixed Assets": 31669,
        "Tangible Assets": 10287,
        "Land": 312,
        "Buildings": 8086,
        "Plant & Machinery": 17305,
        "Construction in Progress": 1510,
        "Other Equipment": 858,
        "Accumulated Depreciation": -17784,
        "Intangible Assets": 18774,
        "Financial Assets": 1517,
        "Investments": 262,
        "Long-term Loan": 0,
        "Other Financial Assets": 1255,
        "Other Fixed Assets": 1091,
        "Deferred Charges": 0,
        "Total Assets": 47072
    },
    "2022": {
        "Current Assets": 14688,
        "Quick Assets": 8187,
        "Cash & Cash Equivalents": 3655,
        "Accounts Receivable - Trade": 4532,
        "Other Quick Assets": 0,
        "Inventories, Net": 5372,
        "Other Current Assets (subtotal)": 1129,
        "Marketable Securities": 238,
        "Short-term Loan": 0,
        "Advance Payments": 0,
        "Other Current Assets": 891,
        "Fixed Assets": 31767,
        "Tangible Assets": 10007,
        "Land": 255,
        "Buildings": 7560,
        "Plant & Machinery": 16455,
        "Construction in Progress": 1728,
        "Other Equipment": 829,
        "Accumulated Depreciation": -16820,
        "Intangible Assets": 17489,
        "Financial Assets": 2530,
        "Investments": 967,
        "Long-term Loan": 0,
        "Other Financial Assets": 1563,
        "Other Fixed Assets": 1741,
        "Deferred Charges": 0,
        "Total Assets": 46455
    },
    "2023": {
        "Current Assets": 16379,
        "Quick Assets": 10683,
        "Cash & Cash Equivalents": 5933,
        "Accounts Receivable - Trade": 4750,
        "Other Quick Assets": 0,
        "Inventories, Net": 4822,
        "Other Current Assets (subtotal)": 874,
        "Marketable Securities": 53,
        "Short-term Loan": 0,
        "Advance Payments": 0,
        "Other Current Assets": 821,
        "Fixed Assets": 34201,
        "Tangible Assets": 9918,
        "Land": 255,
        "Buildings": 7908,
        "Plant & Machinery": 16855,
        "Construction in Progress": 1852,
        "Other Equipment": 759,
        "Accumulated Depreciation": -17711,
        "Intangible Assets": 17153,
        "Financial Assets": 1800,
        "Investments": 244,
        "Long-term Loan": 0,
        "Other Financial Assets": 1556,
        "Other Fixed Assets": 5330,
        "Deferred Charges": 0,
        "Total Assets": 50580
    },
    "2024": {
        "Current Assets": 15884,
        "Quick Assets": 8794,
        "Cash & Cash Equivalents": 5600,
        "Accounts Receivable - Trade": 3194,
        "Other Quick Assets": 0,
        "Inventories, Net": 3698,
        "Other Current Assets (subtotal)": 3392,
        "Marketable Securities": 2128,
        "Short-term Loan": 0,
        "Advance Payments": 0,
        "Other Current Assets": 1264,
        "Fixed Assets": 23984,
        "Tangible Assets": 7953,
        "Land": 200,
        "Buildings": 7432,
        "Plant & Machinery": 14780,
        "Construction in Progress": 994,
        "Other Equipment": 565,
        "Accumulated Depreciation": -16018,
        "Intangible Assets": 7491,
        "Financial Assets": 4036,
        "Investments": 2505,
        "Long-term Loan": 0,
        "Other Financial Assets": 1531,
        "Other Fixed Assets": 4504,
        "Deferred Charges": 0,
        "Total Assets": 39868
    },
    # FY2025 is a PARTIAL key: only the rows that can be read directly off the
    # printed FY2025 statements (balance sheet page 50, PP&E note page 54) plus
    # the four rows that are structurally zero in every verified year.
    #
    # Deliberately omitted, because 3M dropped the separate "Operating lease
    # right of use assets" line in FY2025 and folded it into "Other assets":
    # Other Equipment, Tangible Assets, Fixed Assets, Financial Assets,
    # Investments, Long-term Loan, Other Financial Assets, Other Fixed Assets.
    # Those need the leases and other-assets notes and a mapping judgement that
    # was not supplied with the assignment, so no value is invented for them.
    # compute_metrics scores only the items present here, so an FY2025 run is
    # reported as n/19 rather than being silently graded against guesses.
    "2025": {
        "Cash & Cash Equivalents": 5235,
        "Accounts Receivable - Trade": 3533,
        "Other Quick Assets": 0,
        "Quick Assets": 8768,
        "Inventories, Net": 3661,
        "Marketable Securities": 698,
        "Short-term Loan": 0,
        "Advance Payments": 0,
        "Other Current Assets": 3260,
        "Other Current Assets (subtotal)": 3958,
        "Current Assets": 16387,
        "Land": 202,
        "Buildings": 7729,
        "Plant & Machinery": 15328,
        "Construction in Progress": 663,
        "Accumulated Depreciation": -16821,
        "Intangible Assets": 7522,
        "Deferred Charges": 0,
        "Total Assets": 37733
    }
}

# Benchmark view of the schema: the same 27 rows, with each row's golden answer
# for every stored fiscal year attached.
#
# Derived from ASSET_SCHEMA rather than written out again. The previous version
# repeated all 27 rows by hand, so any edit to a description had to be made in
# two places or the API and the prompt would disagree about what a row means.
BENCHMARK_SCHEMA_METADATA = [
    {
        **row,
        "golden_answers": {
            year: answers.get(row["item"])
            for year, answers in GOLDEN_ANSWERS_STORE.items()
        },
    }
    for row in ASSET_SCHEMA
]
