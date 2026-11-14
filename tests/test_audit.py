import ast
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from mortgage_extraction_claim_audit import phrases
from mortgage_extraction_claim_audit.audit import audit, module_evidence, claims
from mortgage_extraction_claim_audit.__main__ import main

EXPECTED_POS = ('mortgage extraction', 'extract mortgages', 'extracts mortgages', 'extracting mortgages', 'extract mortgage', 'extracts mortgage', 'extracting mortgage', 'mortgage parsing', 'mortgage parser', 'parse mortgages', 'parses mortgages', 'parse mortgage', 'parses mortgage', 'mortgage scanning', 'mortgage scanner', 'scan mortgages', 'scans mortgages', 'scan mortgage', 'scans mortgage', 'loan application extraction', 'extract loan applications', 'extracts loan applications', 'extracting loan applications', 'extract loan application', 'extracts loan application', 'extracting loan application', 'loan document extraction', 'extract loan documents', 'extracts loan documents', 'extracting loan documents', 'extract loan document', 'extracts loan document', 'extracting loan document', 'mortgage document extraction', 'extract mortgage documents', 'extracts mortgage documents', 'extracting mortgage documents', 'extract mortgage document', 'extracts mortgage document', 'extracting mortgage document', 'mortgage data extraction', 'extract mortgage data', 'mortgage field extraction', 'closing disclosure extraction', 'extract closing disclosures', 'extracts closing disclosures', 'extracting closing disclosures', 'extract closing disclosure', 'extracts closing disclosure', 'extracting closing disclosure')
EXPECTED_NEG = ('no mortgage extraction', 'does not extract mortgages', 'does not extract mortgage', 'does not support mortgage extraction', 'without mortgage extraction', 'no loan application extraction', 'does not extract loan applications', 'does not extract loan application', 'does not support loan application extraction', 'without loan application extraction', 'no loan document extraction', 'does not extract loan documents', 'does not extract loan document', 'does not support loan document extraction', 'without loan document extraction', 'mortgage extraction not supported', 'loan application extraction not supported', 'loan document extraction not supported', 'no mortgage parser', 'does not parse mortgages', 'does not parse mortgage', 'no mortgage scanner', 'does not scan mortgages', 'does not scan mortgage')
EXPECTED_NAMES = ('extract_mortgage', 'extract_mortgages', 'parse_mortgage', 'parse_mortgages', 'extract_loan_application', 'extract_loan_applications', 'parse_loan_application', 'parse_loan_applications', 'extract_mortgage_data', 'parse_mortgage_data', 'mortgage_extraction', 'mortgage_extractor', 'mortgage_parser', 'loan_application_extraction', 'extract_mortgage_info', 'parse_mortgage_info', 'mortgage_scan', 'mortgage_scanner', 'scan_mortgage', 'scan_mortgages', 'extract_closing_disclosure', 'parse_closing_disclosure', 'extract_mortgage_terms', 'parse_mortgage_terms')

AZURE = 'from azure.ai.formrecognizer import DocumentAnalysisClient\nc = DocumentAnalysisClient()\n'


class AuditTests(unittest.TestCase):
    def project(self, prose='We extract mortgages.', files=None, options=()):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'README.md').write_text(prose)
            for name, source in (files or {}).items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source)
            result = audit(root)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(['audit', temp, '--json', *options])
            return result, code, json.loads(output.getvalue())

    def test_phrase_oracle(self):
        tree = ast.parse(Path(phrases.__file__).read_text())
        parsed = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)}
        self.assertEqual(parsed['MORTGAGEEXTRACTION'], EXPECTED_POS)
        self.assertEqual(parsed['NOMORTGAGEEXTRACTION'], EXPECTED_NEG)
        self.assertEqual(parsed['GENERIC_NAMES'], EXPECTED_NAMES)
        self.assertEqual((len(EXPECTED_POS), len(EXPECTED_NEG), len(set(EXPECTED_NAMES))), (50, 24, 24))

    def test_bad(self):
        result, code, output = self.project(files={'app.py': 'import mindee'})
        self.assertEqual(code, 2)
        self.assertEqual(result['findings'][0]['rule'], 'documented-mortgage-extraction-claim-false')
        self.assertEqual(result['findings'][0]['severity'], 'HIGH')
        self.assertEqual(output['verdict'], 'FAIL')
        self.assertTrue(output['findings'][0]['message'])

    def test_good(self):
        self.assertEqual(self.project(files={'app.py': 'x.extract_mortgage()'})[1], 0)

    def test_denial(self):
        result, code, _ = self.project('does not extract mortgages', {'app.py': 'x.extract_mortgage()'})
        self.assertEqual(code, 2)
        self.assertEqual([f['rule'] for f in result['findings']], ['documented-no-mortgage-extraction-claim-false'])
        self.assertEqual(result['findings'][0]['severity'], 'HIGH')

    def test_no_claim(self):
        self.assertEqual(self.project('A tool.', {'app.py': 'x.extract_mortgage()'})[1], 0)

    def test_no_source_positive(self):
        self.assertEqual(self.project()[1], 2)

    def test_no_source_denial(self):
        self.assertEqual(self.project('no mortgage extraction')[1], 0)

    def test_test_only_threshold(self):
        for name in ('tests/app.py', 'test_app.py', 'app_test.py'):
            with self.subTest(name=name):
                result, code, _ = self.project(files={name: 'x.extract_mortgage()'})
                self.assertEqual(code, 0)
                self.assertEqual(result['findings'][0]['severity'], 'MEDIUM')
                self.assertEqual(self.project(files={name: 'x.extract_mortgage()'}, options=['--fail-on', 'medium'])[1], 2)

    def test_fences(self):
        for marker in ('```', '~~~', '   ````'):
            self.assertEqual(claims(marker + '\nextract mortgages\n' + marker.strip()), ([], []))
        self.assertTrue(claims('    ```\nextract mortgages')[0])
        self.assertTrue(claims('`extract mortgages`')[0])

    def test_normalization(self):
        self.assertEqual(claims("doesn't extract mortgages"), ([], ['does not extract mortgages']))
        self.assertTrue(claims('EXTRACT-MORTGAGES')[0])
        self.assertFalse(claims('preextract mortgagesuffix')[0])
        self.assertFalse(claims('extract\n\nmortgages')[0])
        for phrase in EXPECTED_NEG:
            self.assertEqual(claims(phrase), ([], [phrase]))
        for phrase in EXPECTED_POS:
            self.assertEqual(claims(phrase), ([phrase], []))

    def test_scope_split(self):
        self.assertEqual(self.project(files={'a.py': AZURE, 'b.py': 'c.begin_analyze_document("prebuilt-mortgage.us.1003")'})[1], 2)

    def test_excluded_directories(self):
        for name in ('fixtures/app.py', 'docs/app.py', 'examples/app.py'):
            self.assertEqual(self.project(files={name: 'x.extract_mortgage()'})[1], 2)

    def test_doc_selection(self):
        self.assertEqual(self.project('neutral', {'nested/docs/page.md': 'extract mortgages'})[1], 2)
        self.assertEqual(self.project('neutral', {'nested/page.md': 'extract mortgages'})[1], 0)

    def test_symlinks(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as other:
            root = Path(temp)
            external = Path(other)
            (root / 'README.md').write_text('extract mortgages')
            (external / 'app.py').write_text('x.extract_mortgage()')
            (root / 'app.py').symlink_to(external / 'app.py')
            (root / 'linked').symlink_to(external, target_is_directory=True)
            self.assertFalse(audit(root)['evidence']['production'])
            (root / 'README.md').unlink()
            (external / 'claim.md').write_text('extract mortgages')
            (root / 'README.md').symlink_to(external / 'claim.md')
            self.assertEqual(audit(root)['verdict'], 'PASS')

    def test_ignore(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'README.md').write_text('extract mortgages')
            (root / 'app.py').write_text('x.extract_mortgage()')
            self.assertEqual(audit(root, ['app.py'])['verdict'], 'FAIL')
            self.assertEqual(audit(root, ['README.md', 'app.py'])['verdict'], 'PASS')

    def test_usage_errors(self):
        for args in ([], ['audit', '--fail-on', 'MEDIUM'], ['audit', '--unknown'], ['audit', '.', '--ignore', 'a', 'b']):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main(args)
                self.assertEqual(error.exception.code, 1)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['audit', '/nonexistent-r200-path']), 1)

    def test_version_and_module(self):
        process = subprocess.run([sys.executable, '-m', 'mortgage_extraction_claim_audit', '--version'], capture_output=True, text=True)
        self.assertEqual((process.returncode, process.stdout.strip()), (0, '0.1.0'))

    def test_console_configuration(self):
        config = Path(__file__).resolve().parents[1] / 'pyproject.toml'
        if config.exists():
            self.assertIn('mortgage-extraction-claim-audit = "mortgage_extraction_claim_audit.__main__:main"', config.read_text())

    def test_self_readme(self):
        readme = Path(__file__).resolve().parents[1] / 'README.md'
        if readme.exists():
            self.assertEqual(claims(readme.read_text()), ([], []))


def add_case(name, source, expected):
    def test(self):
        self.assertEqual(module_evidence(source), expected, source)
    setattr(AuditTests, 'test_' + name, test)


for index, name in enumerate(EXPECTED_NAMES):
    add_case('generic_attribute_%02d' % index, 'x.' + name + '()', True)
    add_case('generic_import_%02d' % index, 'from library import ' + name + ' as operation\noperation()', True)
    add_case('generic_bare_%02d' % index, name + '()', False)
    add_case('generic_shadow_%02d' % index, 'def ' + name + '(): pass\nx.' + name + '()', False)

for index, source in enumerate([
    AZURE + 'c.begin_analyze_document("prebuilt-mortgage.us.1003")',
    'from azure.ai.documentintelligence import DocumentIntelligenceClient as D\nc=D()\nc.begin_analyze_document_from_url("prebuilt-mortgage.us.1004")',
    AZURE + 'c.begin_analyze_document(model_id="prebuilt-mortgage.us.1005")',
    'import azure.ai.formrecognizer as af\nc=af.DocumentAnalysisClient()\nx.begin_analyze_document("prebuilt-mortgage.us.1003")',
    'import azure.ai.documentintelligence\nc=azure.ai.documentintelligence.DocumentIntelligenceClient()\nx.begin_analyze_document("prebuilt-mortgage.us.1003")',
    'from azure.ai import formrecognizer as af\nc=af.DocumentAnalysisClient()\nx.begin_analyze_document("prebuilt-mortgage.us.1003")',
]):
    add_case('azure_positive_%02d' % index, source, True)

for index, model in enumerate(['prebuilt-invoice', 'prebuilt-receipt', 'prebuilt-layout', 'prebuilt-read', 'prebuilt-idDocument', 'prebuilt-check.us', 'prebuilt-tax.us', 'prebuilt-bankStatement.us', 'prebuilt-payStub.us', 'prebuilt-healthInsuranceCard.us', 'prebuilt-businessCard', 'prebuilt-creditCard', 'prebuilt-contract', 'prebuilt-mortgage.us', 'prebuilt-mortgage-1003', 'prebuilt-mortgage-1004', 'prebuilt-mortgage-1005', 'prebuilt-mortgage-1008', 'prebuilt-mortgage.us.1007', 'prebuilt-mortgage.us.1010', 'prebuilt-Mortgage.us.1003', 'prebuilt-mortgage.us.closingdisclosure', 'other']):
    add_case('azure_wrong_model_%02d' % index, AZURE + 'c.begin_analyze_document(' + repr(model) + ')', False)

for index, product in enumerate(['InvoiceV4', 'ReceiptV5', 'PassportV1', 'FinancialDocumentV1', 'BankCheckV1', 'BankAccountDetailsV2', 'PayslipV2', 'PayslipV3', 'HealthcareCardV1', 'BusinessCardV1', 'CustomV1', 'ContractV1']):
    add_case('mindee_product_%02d' % index, 'from mindee import Client, product\nc=Client()\nc.parse(product.' + product + ', input_doc)', False)

VERYFI = ('process_any_document process_any_document_url process_document process_document_url process_w2_document process_w9_document process_w8_document process_check process_check_url process_check_with_remittance process_check_with_remittance_url process_bank_statement_document process_bank_statement_document_url process_bussines_card_document process_bussines_card_document_url classify_document get_business_cards get_business_card delete_business_card process_mortgage_document process_mortgage_document_url').split()
for index, method in enumerate(VERYFI):
    add_case('veryfi_%02d' % index, 'from veryfi import Client\nc=Client()\nc.' + method + '(doc)', False)

NEGATIVE_SOURCES = [
    'import mindee', 'import veryfi', 'import azure.ai.formrecognizer',
    'from mindee import Client\nc=Client()', 'from veryfi import Client\nc=Client()', AZURE,
    'x.begin_analyze_document("prebuilt-mortgage.us.1003")',
    'import azure\nc=azure.DocumentAnalysisClient()\nc.begin_analyze_document("prebuilt-mortgage.us.1003")',
    'from other import DocumentAnalysisClient\nc=DocumentAnalysisClient()\nc.begin_analyze_document("prebuilt-mortgage.us.1003")',
    'textract.analyze_document()', 'textract.analyze_expense()', 'textract.start_document_analysis()', 'textract.get_expense_analysis()',
    'pdfplumber.extract_text()', 'fitz.extract_text()', 'pypdf.extract_text()', 'PyPDF2.extract_text()', 'pdfminer.extract_text()',
    'pytesseract.image_to_string()', 'pandas.read_csv()', 'pandas.read_excel()',
    'camelot.read_pdf()', 'tabula.read_pdf()', 'tabula.convert_into()',
    'pdfplumber.extract_table()', 'pdfplumber.extract_tables()', 'pdfplumber.find_table()', 'pdfplumber.find_tables()', 'fitz.find_tables()',
    'import re\ntext=ocr.image_to_string(doc)\nfields={"title": re.search("Title: (.*)", text)}',
    'text="mortgage text"\nfields=text.split(":")',
    'import subprocess\nsubprocess.run(["mindee", "parse", "mortgage"])',
    'import subprocess\nsubprocess.run(["veryfi", "mortgage"])',
    '# x.extract_mortgage()\ns="x.extract_mortgage()"', 'x.extract_mortgage', 'x.extract_mortgage(',
    'from lib import extract_mortgage as run\nrun=lambda:None\nrun()',
    'from lib import extract_mortgage as run\nrun: object = None\nrun()',
    'from lib import extract_mortgage as run\nwith manager() as run:\n run()',
    'from lib import extract_mortgage as run\nasync def f():\n async with manager() as run:\n  run()',
    'class X:\n def extract_mortgage(self): pass\nx.extract_mortgage()',
    'class extract_mortgage: pass\nx.extract_mortgage()',
    'from azure.ai.formrecognizer import DocumentAnalysisClient\ndef DocumentAnalysisClient(): pass\nc=DocumentAnalysisClient()\nc.begin_analyze_document("prebuilt-mortgage.us.1003")',
]
for index, source in enumerate(NEGATIVE_SOURCES):
    add_case('not_evidence_%02d' % index, source, False)

add_case('azure_similar_module_not_gate', 'import azure.ai.formrecognizer_fake\nc=azure.DocumentAnalysisClient()\nc.begin_analyze_document("prebuilt-mortgage.us.1003")', False)
add_case('azure_rebound_import', 'import azure.ai.formrecognizer as af\naf = object()\nc=af.DocumentAnalysisClient()\nc.begin_analyze_document("prebuilt-mortgage.us.1003")', False)
add_case('generic_module_alias', 'import library as lib\nlib.parse_mortgage_terms()', True)
add_case('generic_alias_local_definition', 'from library import extract_mortgage as run\ndef run(): pass\nrun()', False)

for index, model in enumerate(('prebuilt-mortgage.us.1003', 'prebuilt-mortgage.us.1004', 'prebuilt-mortgage.us.1005', 'prebuilt-mortgage.us.1008', 'prebuilt-mortgage.us.closingDisclosure')):
    add_case('azure_all_models_%02d' % index, AZURE + 'c.begin_analyze_document(' + repr(model) + ')', True)

if __name__ == '__main__':
    unittest.main()
