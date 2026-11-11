"""So sánh hai file eval: điểm từng case, model calls, token, sự kiện validation.

Ví dụ: python compare_evals.py eval_before.json eval_after.json
"""
import json
import sys
from pathlib import Path


def tokens(usage):
    total = 0
    for u in usage or []:
        if not isinstance(u, dict):
            continue
        if 'total_tokens' in u:
            total += u.get('total_tokens') or 0
        else:  # Anthropic
            total += (u.get('input_tokens') or 0) + (u.get('output_tokens') or 0)
    return total


def stats(case):
    result, grade = case.get('result', {}), case.get('grade', {})
    trace = result.get('trace', [])
    return {'score': grade.get('score'), 'status': result.get('status'),
            'calls': len(result.get('usage') or []), 'tokens': tokens(result.get('usage')),
            'judge_tokens': tokens([grade.get('judge_usage')]),
            'tools': sum(t.get('event') == 'tool' for t in trace),
            'gate': sum(t.get('event') == 'validation_missing_source' for t in trace),
            'violations': (grade.get('mechanical') or {}).get('violations', [])}


def main(before_path, after_path):
    before = json.loads(Path(before_path).read_text(encoding='utf-8'))
    after = json.loads(Path(after_path).read_text(encoding='utf-8'))
    b_cases = {c['id']: stats(c) for c in before['cases']}
    a_cases = {c['id']: stats(c) for c in after['cases']}
    print(f"Config before: {before['config']}")
    print(f"Config after : {after['config']}")
    print(f"Tổng điểm: {before['summary'].get('score_0_100')} -> {after['summary'].get('score_0_100')}\n")
    header = f"{'case':5} {'before':>7} {'after':>7} {'delta':>6}  {'calls':>9} {'tokens':>15} {'gate':>4}  status"
    print(header)
    print('-' * len(header))
    tot = {'bc': 0, 'ac': 0, 'bt': 0, 'at': 0}
    for cid in sorted(set(b_cases) | set(a_cases), key=lambda x: (x[0], int(x[1:]) if x[1:].isdigit() else 0)):
        b, a = b_cases.get(cid, {}), a_cases.get(cid, {})
        bs, as_ = b.get('score'), a.get('score')
        delta = f'{as_ - bs:+d}' if isinstance(bs, int) and isinstance(as_, int) else '  n/a'
        tot['bc'] += b.get('calls', 0); tot['ac'] += a.get('calls', 0)
        tot['bt'] += b.get('tokens', 0); tot['at'] += a.get('tokens', 0)
        print(f"{cid:5} {str(bs):>7} {str(as_):>7} {delta:>6}  {b.get('calls', 0):>4}->{a.get('calls', 0):<4} "
              f"{b.get('tokens', 0):>7}->{a.get('tokens', 0):<7} {a.get('gate', 0):>4}  {b.get('status')}->{a.get('status')}")
        for v in a.get('violations', []):
            print(f'      after violation: {v}')
    print('-' * len(header))
    print(f"Model calls (agent): {tot['bc']} -> {tot['ac']};  agent tokens: {tot['bt']} -> {tot['at']}")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit('Cách dùng: python compare_evals.py eval_before.json eval_after.json')
    main(sys.argv[1], sys.argv[2])
