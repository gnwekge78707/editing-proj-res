#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import re, json
from pathlib import Path

IMG_EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}

def b_input(name):
    m = re.match(r'^(?P<base>.+)-Input\.[^.]+$', name, re.IGNORECASE)
    return m.group('base') if m else None

def b_target(name):
    m = re.match(r'^(?P<base>.+)-Target\.[^.]+$', name, re.IGNORECASE)
    return m.group('base') if m else None

def b_prompt(name):
    m = re.match(r'^(?P<base>.+)-Prompt.*\.txt$', name, re.IGNORECASE)
    return m.group('base') if m else None

def parse_output_base(name: str):
    # 例：24_Expert8-0-0-Best-Input.jpg_ip2p_Expert8-0-0-Best-Target.jpg.png
    m = re.match(r'^\d+_(?P<input>.+-Input\.[^.]+)_ip2p_(?P<target>.+-Target\.[^.]+)\.(?:png|jpg|jpeg|webp|bmp)$',
                 name, re.IGNORECASE)
    if not m:
        return None
    in_base = b_input(m.group('input'))
    tg_base = b_target(m.group('target'))
    return in_base or tg_base

def scan(inputs_dir: Path, outputs_dir: Path):
    inputs, targets, prompts = {}, {}, {}
    for p in inputs_dir.iterdir():
        if not p.is_file(): continue
        n, ext = p.name, p.suffix.lower()
        if ext in IMG_EXTS:
            if '-Input.' in n and b_input(n):  inputs[b_input(n)] = p
            elif '-Target.' in n and b_target(n): targets[b_target(n)] = p
        elif ext == '.txt':
            base = b_prompt(n)
            if base:
                try:    prompts[base] = p.read_text(encoding='utf-8').strip()
                except: prompts[base] = p.read_text(errors='ignore').strip()

    outputs = {}
    for p in outputs_dir.iterdir():
        if p.is_file() and p.suffix.lower() in IMG_EXTS:
            base = parse_output_base(p.name)
            if base: outputs[base] = p

    bases = sorted((set(inputs) & set(targets)) & set(outputs))
    records = []
    for b in bases:
        records.append({
            'id': b,
            'input': inputs[b].as_posix(),
            'target': targets[b].as_posix(),
            'output': outputs[b].as_posix(),
            'prompt': prompts.get(b, '')
        })

    stats = {
        'missing_output': sorted((set(inputs) & set(targets)) - set(outputs)),
        'missing_input_or_target': sorted(set(outputs) - (set(inputs) & set(targets)))
    }
    return records, stats

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--inputs', default='inputs', help='包含 Input/Target/Prompt 的目录')
    parser.add_argument('--outputs', default='outputs', help='包含模型 Output 的目录')
    parser.add_argument('--root', default='.', help='相对路径基准（index.html 所在目录）')
    parser.add_argument('--out', default='manifest.json', help='输出清单文件路径')
    args = parser.parse_args()

    inputs_dir = Path(args.inputs).resolve()
    outputs_dir = Path(args.outputs).resolve()
    root = Path(args.root).resolve()

    records, stats = scan(inputs_dir, outputs_dir)

    # 路径转为相对 index.html 的 posix 形式
    for r in records:
        for k in ['input','target','output']:
            r[k] = str(Path(r[k]).resolve().relative_to(root).as_posix())

    Path(args.out).write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"wrote {args.out} with {len(records)} items")
    if stats['missing_output']:
        print('[WARN] 找不到 output 的样本：', len(stats['missing_output']))
    if stats['missing_input_or_target']:
        print('[WARN] output 无法匹配到 input/target 的样本：', len(stats['missing_input_or_target']))
