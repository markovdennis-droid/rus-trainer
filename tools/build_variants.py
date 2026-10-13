# -*- coding: utf-8 -*-
"""
Сборка вариантов из JSON в JS.

Тренажёр должен открываться и с диска (file://), и с GitHub Pages.
fetch() локальный JSON не отдаёт — браузер блокирует его политикой
источника, — а <script src> отдаёт. Поэтому каждый bank/variants/*.json
заворачивается в одноимённый .js, который кладёт данные в window.VARIANTS.

JSON остаётся источником правды: его читают валидатор и генераторы.

Запуск:  python3 -I tools/build_variants.py
"""
import json
import sys
from pathlib import Path

DIR = Path(__file__).resolve().parent.parent / "bank" / "variants"


def main() -> int:
    # index.json — результат сборки, а не вариант
    files = sorted(p for p in DIR.glob("*.json") if p.name != "index.json")
    if not files:
        print(f"нет вариантов в {DIR}")
        return 1
    index = []
    for src in files:
        data = json.loads(src.read_text("utf-8"))
        vid = data.get("id") or src.stem
        out = src.with_suffix(".js")
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        out.write_text(
            "window.VARIANTS=window.VARIANTS||{};\n"
            f"window.VARIANTS[{json.dumps(vid)}]={body};\n",
            encoding="utf-8",
        )
        index.append({"id": vid, "title": data.get("title", vid), "file": out.name})
        print(f"{src.name} -> {out.name}  ({out.stat().st_size // 1024} КБ, заданий {len(data['tasks'])})")
    (DIR / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"\nвариантов собрано: {len(index)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
