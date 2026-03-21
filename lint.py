#!/usr/bin/env python3
"""memo-app index.html の簡易リンター。
PostToolUse hookから呼ばれ、HTML構文とJS基本チェックを行う。"""

import sys
import re
from html.parser import HTMLParser

FILE = "/home/above/knowledge-base/memo-app/index.html"

class HTMLLinter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.errors = []
        self.stack = []
        self.void_elements = {
            'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
            'link', 'meta', 'param', 'source', 'track', 'wbr'
        }

    def handle_starttag(self, tag, attrs):
        if tag not in self.void_elements:
            self.stack.append((tag, self.getpos()))

    def handle_endtag(self, tag):
        if tag in self.void_elements:
            return
        if not self.stack:
            self.errors.append(f"L{self.getpos()[0]}: 閉じタグ </{tag}> に対応する開きタグがない")
            return
        expected_tag, pos = self.stack.pop()
        if expected_tag != tag:
            self.errors.append(
                f"L{self.getpos()[0]}: </{tag}> が出現したが <{expected_tag}> (L{pos[0]}) の閉じタグを期待")

def check_js_brackets(content):
    """scriptタグ内の括弧の対応をチェック"""
    errors = []
    script_match = re.search(r'<script>([\s\S]*?)</script>', content)
    if not script_match:
        return errors
    js = script_match.group(1)
    # 括弧の対応チェック（文字列リテラル内は簡易的にスキップ）
    pairs = {'{': '}', '(': ')', '[': ']'}
    closing = {v: k for k, v in pairs.items()}
    stack = []
    in_string = None
    i = 0
    line = 1
    while i < len(js):
        c = js[i]
        if c == '\n':
            line += 1
        # 文字列リテラルのスキップ
        if in_string:
            if c == '\\':
                i += 2
                continue
            if c == in_string:
                in_string = None
            i += 1
            continue
        if c in ('"', "'", '`'):
            in_string = c
            i += 1
            continue
        # コメント・正規表現のスキップ
        if c == '/' and i + 1 < len(js):
            if js[i + 1] == '/':
                while i < len(js) and js[i] != '\n':
                    i += 1
                continue
            if js[i + 1] == '*':
                end = js.find('*/', i + 2)
                if end == -1:
                    errors.append(f"L{line}: 閉じられていないブロックコメント")
                    break
                line += js[i:end].count('\n')
                i = end + 2
                continue
            # 正規表現リテラルの簡易スキップ（直前が演算子・括弧・カンマ等の場合）
            prev_char = js[i - 1] if i > 0 else ''
            prev_stripped = js[:i].rstrip()
            if prev_stripped and prev_stripped[-1] in '=(:,;!&|?~^%*/+->[\n{':
                i += 1
                while i < len(js) and js[i] != '\n':
                    if js[i] == '\\':
                        i += 2
                        continue
                    if js[i] == '/':
                        i += 1
                        # フラグをスキップ
                        while i < len(js) and js[i].isalpha():
                            i += 1
                        break
                    i += 1
                continue
        if c in pairs:
            stack.append((c, line))
        elif c in closing:
            if not stack:
                errors.append(f"L{line}: 閉じ括弧 '{c}' に対応する開き括弧がない")
            else:
                open_c, open_line = stack.pop()
                if pairs[open_c] != c:
                    errors.append(f"L{line}: '{c}' が出現したが '{pairs[open_c]}' を期待 (L{open_line}で開始)")
        i += 1
    for open_c, open_line in stack:
        errors.append(f"L{open_line}: '{open_c}' が閉じられていない")
    return errors

def check_ids(content):
    """重複IDのチェック"""
    ids = re.findall(r'id="([^"]+)"', content)
    seen = {}
    errors = []
    for id_val in ids:
        if id_val in seen:
            errors.append(f"重複ID: '{id_val}'")
        seen[id_val] = True
    return errors

def main():
    try:
        with open(FILE) as f:
            content = f.read()
    except FileNotFoundError:
        return 0  # ファイルが無ければスキップ

    errors = []

    # HTML構文チェック
    linter = HTMLLinter()
    try:
        linter.feed(content)
        errors.extend(linter.errors)
        for tag, pos in linter.stack:
            errors.append(f"L{pos[0]}: <{tag}> が閉じられていない")
    except Exception as e:
        errors.append(f"HTML解析エラー: {e}")

    # JS括弧チェック
    errors.extend(check_js_brackets(content))

    # 重複IDチェック
    errors.extend(check_ids(content))

    if errors:
        print("memo-app lint errors:")
        for e in errors:
            print(f"  {e}")
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
