"""Validate that roadmap_template.docx defines all styles required by report_generator.py.
Run from the repo root:
    python validate_template.py
"""
import os
from docx import Document

TEMPLATE = os.path.join('assets', 'roadmap_template.docx')

REQUIRED_STYLES = [
    ('Heading 1',   'paragraph', 'Cover heading and section headings'),
    ('Heading 2',   'paragraph', 'Domain / phase sub-headings'),
    ('Heading 3',   'paragraph', 'Finding title sub-headings'),
    ('Normal',      'paragraph', 'Body text paragraphs'),
    ('List Bullet', 'paragraph', 'Root cause / economic impact bullet lists'),
    ('Table Grid',  'table',     'All tables'),
]

if not os.path.exists(TEMPLATE):
    print(f"Template not found: {TEMPLATE}")
    raise SystemExit(1)

doc = Document(TEMPLATE)
defined = {s.name: s.type for s in doc.styles}

print(f"\nTemplate: {TEMPLATE}")
print(f"Total styles defined: {len(defined)}\n")

print("REQUIRED STYLES CHECK:")
print(f"{'Style':<16} {'Status':<10} {'Used for'}")
print("─" * 72)

missing = []
for name, stype, usage in REQUIRED_STYLES:
    if name in defined:
        print(f"{name:<16} {'✓ present':<10} {usage}")
    else:
        print(f"{name:<16} {'✗ MISSING':<10} {usage}")
        missing.append(name)

if missing:
    print(f"\nMissing styles: {', '.join(missing)}")
    print("Add these styles to your template in Word (Home → Styles pane) and re-save as .docx")
else:
    print("\nAll required styles present — template is ready.")

print("\nALL STYLES IN TEMPLATE:")
for name, stype in sorted(defined.items()):
    print(f"  {name}")
