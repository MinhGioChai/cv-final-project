"""Record/import Pet-only source-label QA; never overwrite v2 packets or imply two reviewers."""
import argparse
import json
from pathlib import Path

from vlmbench.io_utils import manifest_bytes, atomic_bytes, write_json
from vlmbench.pet_review import create_review, import_review, inside


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['record', 'import'])
    p.add_argument('--manifest', default='data/main/preparation_v3/oxford_pet_bilingual_draft.csv')
    p.add_argument('--attestation', help='JSON containing an actual user declaration, not a generated reviewer')
    p.add_argument('--review', required=True)
    p.add_argument('--output')
    p.add_argument('--audit')
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    root = Path.cwd().resolve()
    review_path = inside(root, a.review)
    if a.action == 'record':
        if not a.attestation or a.output or a.audit or a.dry_run:
            p.error('record requires --attestation; output/audit/dry-run belong to import')
        if review_path.exists():
            raise ValueError('Preserve existing review; use a new path')
        review = create_review(root, a.manifest, json.loads(inside(root, a.attestation).read_text(encoding='utf-8')))
        write_json(review_path, review)
        print(json.dumps({'review': a.review, 'rows': len(review['decisions']), 'policy': review['policy']}))
    else:
        if not a.output or not a.audit or a.attestation:
            p.error('import requires --output/--audit, not --attestation')
        output, audit = inside(root, a.output), inside(root, a.audit)
        if len({review_path, output, audit}) != 3 or output.exists() or audit.exists():
            raise ValueError('Use distinct new output/audit paths; preserve existing files')
        rows, report = import_review(root, a.review)
        if not a.dry_run:
            atomic_bytes(output, manifest_bytes(rows)); write_json(audit, report)
        print(json.dumps({'dry_run': a.dry_run, **report}, ensure_ascii=False))


if __name__ == '__main__':
    main()
