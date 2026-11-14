# Documentation claim auditor

An offline static auditor comparing documentation promises with recognized calls in Python source. It reports unsupported promises and contradictions without executing project code. Requires Python 3.9 or newer; no runtime dependencies.

## Installation and usage

```sh
python3 -m pip install .
mortgage-extraction-claim-audit audit .
mortgage-extraction-claim-audit audit . --json --verbose --ignore build --ignore dist --fail-on medium
python3 -m mortgage_extraction_claim_audit audit .
mortgage-extraction-claim-audit --version
```

The repository defaults to the current directory. Repeatable ignore prefixes select relative subtrees. Exit 0 means PASS at the selected threshold, 2 means findings at that threshold, and 1 means usage or I/O error. The default threshold is high; medium also fails on evidence found only in tests. JSON includes verdict, findings with rule, severity, message and locations, and evidence paths. Verbose output lists evidence paths.

## Matching rules

Root README.md and Markdown files with a docs path component are checked. Fenced blocks using backticks or tildes with up to three leading spaces are excluded; inline code counts. Paragraphs split on blank lines. Normalization lowercases, expands contractions, replaces hyphens with spaces and collapses whitespace. Boundary matches use longest phrases first with alphabetical ties. Denial spans are removed before positive matching. Each family produces at most one finding.

Source is parsed with AST and never executed. Symlinks are excluded. Fixtures, docs and examples provide no evidence; tests count separately. Invalid syntax provides no evidence. Imports and aliases resolve within one module. Local function, method and class definitions shadow route names. Assignments, annotated assignments and context manager bindings shadow imported names. Bare imports and references do not count. Generic attribute calls accept any base; bare names require an imported recognized name. A positive promise without source fails; a denial without source passes.

The exact vocabulary and evidence rules follow as reference data.

```text
mortgage extraction
extract mortgages
extracts mortgages
extracting mortgages
extract mortgage
extracts mortgage
extracting mortgage
mortgage parsing
mortgage parser
parse mortgages
parses mortgages
parse mortgage
parses mortgage
mortgage scanning
mortgage scanner
scan mortgages
scans mortgages
scan mortgage
scans mortgage
loan application extraction
extract loan applications
extracts loan applications
extracting loan applications
extract loan application
extracts loan application
extracting loan application
loan document extraction
extract loan documents
extracts loan documents
extracting loan documents
extract loan document
extracts loan document
extracting loan document
mortgage document extraction
extract mortgage documents
extracts mortgage documents
extracting mortgage documents
extract mortgage document
extracts mortgage document
extracting mortgage document
mortgage data extraction
extract mortgage data
mortgage field extraction
closing disclosure extraction
extract closing disclosures
extracts closing disclosures
extracting closing disclosures
extract closing disclosure
extracts closing disclosure
extracting closing disclosure
no mortgage extraction
does not extract mortgages
does not extract mortgage
does not support mortgage extraction
without mortgage extraction
no loan application extraction
does not extract loan applications
does not extract loan application
does not support loan application extraction
without loan application extraction
no loan document extraction
does not extract loan documents
does not extract loan document
does not support loan document extraction
without loan document extraction
mortgage extraction not supported
loan application extraction not supported
loan document extraction not supported
no mortgage parser
does not parse mortgages
does not parse mortgage
no mortgage scanner
does not scan mortgages
does not scan mortgage

Generic names:
extract_mortgage, extract_mortgages, parse_mortgage, parse_mortgages, extract_loan_application, extract_loan_applications, parse_loan_application, parse_loan_applications, extract_mortgage_data, parse_mortgage_data, mortgage_extraction, mortgage_extractor, mortgage_parser, loan_application_extraction, extract_mortgage_info, parse_mortgage_info, mortgage_scan, mortgage_scanner, scan_mortgage, scan_mortgages, extract_closing_disclosure, parse_closing_disclosure, extract_mortgage_terms, parse_mortgage_terms

documented-mortgage-extraction-claim-false HIGH (MEDIUM with test-only evidence)
documented-no-mortgage-extraction-claim-false HIGH

DocumentAnalysisClient / DocumentIntelligenceClient construction +
begin_analyze_document / begin_analyze_document_from_url call with
model id exactly one of "prebuilt-mortgage.us.1003",
"prebuilt-mortgage.us.1004", "prebuilt-mortgage.us.1005",
"prebuilt-mortgage.us.1008", "prebuilt-mortgage.us.closingDisclosure"
(pair, 5); import gate
azure.ai.formrecognizer or azure.ai.documentintelligence. Match is
case-sensitive and exact. NOTE: the models are GA in v4.0
(2024-11-30) — the Learn model-overview page states "This content
applies to: v3.1 (GA) | Latest version: v4.0 (GA)" and lists the
five US mortgage document model ids for v4.0. The v3.1 hyphen
forms ("prebuilt-mortgage-1003", "prebuilt-mortgage-1004", and
so on) are NOT evidence: this family targets the v4.0 ids only.
The tool still counts the call, since it detects the call in
source, not whether the call succeeds against a current API
version.

## mindee names (implementation MUST match exactly)

NO mindee route: mindee has no mortgage product in the Python
SDK. The 4.22.0 wheel, inspected 2026-11-13, contains no
mortgage product directory and no Mortgage product class (grep
"mortgage" across the whole wheel returns zero hits), so a
mindee parse with ANY product is NOT evidence.

## veryfi names (implementation MUST match exactly)

NO veryfi route: veryfi has no mortgage method in the Python
SDK. The 5.1.0 wheel, inspected 2026-11-13, contains no
process_mortgage_document / process_mortgage_document_url
method and no mortgage module, so a veryfi call of ANY kind is
NOT evidence. Veryfi process_any_document / process_any_document_url
is generic AnyDocs configurable extraction, NOT evidence. The
sole "mortgage" hit in the wheel is the words "Mortgage Payments"
as an example transaction category for the bank-statement endpoint
in the package METADATA README — a bank-statement category, not a
mortgage document operation.

```

## Honest limitations

These reference notes explain ambiguity and exclusions.

```text
- The bare phrases "mortgage extraction" / "extract mortgage" /
  "extract mortgages" are deliberately MORTGAGEEXTRACTION phrases:
  in document-tool docs they almost always name mortgage
  extraction. But "mortgage" can also name a mortgage the tool
  merely stores, tracks, or manages (a mortgage calculator, a
  mortgage payment tracker, a loan servicing dashboard) without
  extracting fields from a mortgage document: a doc that means
  storing, tracking, or managing mortgages, not extracting fields
  from them, is a false positive; the tool flags the claim, only
  the code decides.
- "loan application extraction" / "extract loan application(s)" are
  deliberately phrases: the Azure 1003 model covers loan
  applications. But "loan application" is a generic phrase — a doc
  can say "extract loan application" about a web form the tool
  merely submits, or a loan application workflow the tool merely
  routes: a doc that means submitting or routing a loan
  application, not extracting fields from a loan application
  document, is a false positive; the tool flags the claim, only
  the code decides.
- "loan document extraction" / "extract loan document(s)" are
  deliberately phrases: "loan document" can also name any loan
  paperwork the tool merely stores or files. The tool flags the
  claim; only the code decides.
- "closing disclosure extraction" / "extract closing disclosure(s)"
  are deliberately phrases: a closing disclosure is a mortgage
  document type. But a doc can mention a closing disclosure the
  tool merely displays or archives. The tool flags the claim;
  only the code decides.
- "mortgage scanning" / "scan mortgage(s)" are deliberately
  phrases: "scanning" a mortgage document can mean merely
  photographing it or OCRing it into raw text, with no structured
  field extraction. The tool flags the claim; only the code
  decides.
- A generic `extract_mortgage(` / `parse_mortgage(` /
  `extract_loan_application(` call can name a string parser for text
  the user typed in rather than a document extractor: the tool
  counts the call, the claim plus the code decide — and a
  subprocess call invoking an external CLI is NOT evidence by
  design, so a thin wrapper that only calls subprocess fails.
- Azure `begin_analyze_document` with a model id of
  "prebuilt-mortgage.us.1003", "prebuilt-mortgage.us.1004",
  "prebuilt-mortgage.us.1005", "prebuilt-mortgage.us.1008", or
  "prebuilt-mortgage.us.closingDisclosure" counts as evidence: the
  models are GA in v4.0 (2024-11-30) and the tool detects the
  client call in source, not whether the call succeeds against a
  current API version. 
- Azure `begin_analyze_document` with "prebuilt-mortgage.us"
  (bare, no form suffix) is NOT detected: no such model id exists
  — a form suffix (1003, 1004, 1005, 1008, closingDisclosure) is
  required. 
- Azure `begin_analyze_document` with "prebuilt-mortgage-1003"
  (v3.1 hyphen form) is NOT detected: this family targets the
  v4.0 ids only. 
- Azure `begin_analyze_document` with "prebuilt-mortgage.us.1007"
  or "prebuilt-mortgage.us.1010" is NOT detected: no such v4.0
  model ids exist — the v4.0 mortgage table lists only 1003,
  1004, 1005, 1008, and closingDisclosure. 
- Azure `begin_analyze_document` with "prebuilt-Mortgage.us.1003"
  is NOT detected: model ids are matched case-sensitively and
  exactly. 
- Azure `begin_analyze_document` with
  "prebuilt-mortgage.us.closingdisclosure" is NOT detected: the
  real id has a capital D ("closingDisclosure"). 
- Mindee `parse` with ANY product is NOT detected: mindee has no
  mortgage product in the Python SDK (4.22.0 wheel inspected
  2026-11-13 — the word "mortgage" does not appear anywhere in
  the wheel), so no mindee parse can be a mortgage extraction
  operation. 
- Veryfi `process_any_document` / `process_any_document_url` are
  NOT detected: AnyDocs is generic configurable extraction, not a
  mortgage operation. 
- Veryfi `process_document` is NOT detected: it processes generic
  receipts and invoices. Only a mortgage method would count
  here, and none exists. 
- Veryfi `process_w2_document` / `process_w9_document` /
  `process_w8_document` are NOT detected: tax forms are a separate
  document type covered by the tax-form family. 
- Veryfi `process_check` / `process_check_url` /
  `process_check_with_remittance` /
  `process_check_with_remittance_url` are NOT detected: checks are
  a separate document type covered by the bank-check family. Say
  so in the README.
- Veryfi `process_bank_statement_document` /
  `process_bank_statement_document_url` are NOT detected: bank
  statements are a separate document type covered by the
  bank-statement family's domain. The words "Mortgage Payments"
  in veryfi's bank-statement category examples are transaction
  categories, not mortgage document extraction. 
- Veryfi `process_bussines_card_document` /
  `process_bussines_card_document_url` are NOT detected: business
  cards are a separate document type covered by the
  business-card family. 
- Veryfi `get_business_cards` / `get_business_card` /
  `delete_business_card` are NOT detected: retrieval and
  management, not extraction. 
- Veryfi `classify_document` is NOT detected: classification, not
  extraction. 
- Azure `begin_analyze_document` with "prebuilt-invoice" /
  "prebuilt-receipt" / "prebuilt-layout" / "prebuilt-idDocument" /
  "prebuilt-check.us" / "prebuilt-tax.us" /
  "prebuilt-bankStatement.us" / "prebuilt-payStub.us" /
  "prebuilt-healthInsuranceCard.us" / "prebuilt-businessCard" /
  "prebuilt-creditCard" / "prebuilt-contract" is NOT detected, for
  the same reason: invoices, receipts, layouts, ID documents,
  checks, tax forms, bank statements, pay stubs, health insurance
  cards, business cards, credit cards, and contracts are separate
  document types covered by their own families. 
- Mindee `parse` with InvoiceV4 / ReceiptV5 / PassportV1 /
  FinancialDocumentV1 / BankCheckV1 / BankAccountDetailsV2 /
  PayslipV2 / PayslipV3 / HealthcareCardV1 / BusinessCardV1 /
  CustomV1 is NOT detected: those are other document types, and
  mindee has no mortgage product at all. 
- Textract `analyze_document` / `analyze_expense` /
  `start_document_analysis` / `get_expense_analysis` are NOT
  detected: generic document and expense analysis are not
  mortgage extraction, and Textract has no mortgage operation.
  
- A hand-rolled extraction from OCR text (`re.search` /
  `re.findall` on extracted text plus manual field assembly, no
  listed call) is NOT detected: the tool requires a listed call.
  
- The mindee CLI, the veryfi CLI, and any other external mortgage
  tool invoked through subprocess are NOT detected:
  subprocess calls invoking an external CLI are NOT evidence by
  design. 
- Azure Document Intelligence, Mindee, and Veryfi are cloud APIs:
  the tool detects the client call in source, not whether
  credentials are configured or the call succeeds. 
- "extract borrower name" / "extract loan amount" / "extract
  property address" / "extract closing costs" claims are NOT in
  the phrase lists: borrower names, loan amounts, property
  addresses, and closing costs are mortgage data points, not
  mortgage extraction claims on their own. 
- Invoice extraction claims ("extract invoices", "invoice
  extraction"), receipt extraction claims ("extract receipts",
  "receipt extraction"), ID document extraction claims ("extract
  passports", "passport extraction"), bank check extraction claims
  ("extract bank checks", "check extraction"), bank statement
  extraction claims ("extract bank statements", "statement
  extraction"), tax form extraction claims ("extract tax forms",
  "extract w2 forms", "1099 extraction"), pay stub extraction
  claims ("extract pay stubs", "payslip extraction"), health
  insurance card extraction claims ("extract health insurance
  cards", "health insurance card extraction"), business card
  extraction claims ("extract business cards", "business card
  extraction"), credit card extraction claims ("extract credit
  cards", "credit card extraction"), and contract extraction
  claims ("extract contracts", "contract extraction") are NOT in
  the phrase lists: this family covers mortgages only. 
- Mortgage management claims ("manage mortgages", "track
  mortgages", "mortgage calculator", "mortgage servicing") are NOT
  in the phrase lists: managing, tracking, or calculating a
  mortgage is not extracting fields from a mortgage document.
  
- As with every family: static pattern matching, not semantic
  judgement; dead code counts; alias chains the tracer cannot follow
  are missed; exact phrases only, not semantics; denial handling
  depends on the denial phrase list; each route must sit in a single
  module.

Additional exclusions: plain text through pdfplumber, fitz, pypdf, PyPDF2 or pdfminer; OCR through pytesseract; CSV/spreadsheets through pandas; tables through camelot, tabula, pdfplumber or fitz. Strings, comments, bare references and syntax-invalid files do not count.
```

## Differentiation

The checked capability concerns structured fields from US lending documents. The invoice, receipt, id-document, bank-check, bank-statement, tax-form, pay-stub, health-insurance-card, business-card, credit-card and contract extraction families check other document types. A 1098 remains a tax form. OCR checks text recognition and table extraction checks tabular structure; neither establishes the checked operation. This auditor does not validate returned fields, credentials or service availability.

## Development

```sh
python3 -m unittest discover
python3 -m venv .venv
.venv/bin/python3 -m pip install build
.venv/bin/python3 -m build
```

Both distributions include the tests. The tool uses only the standard library, makes no network calls and writes only to standard output or standard error.
