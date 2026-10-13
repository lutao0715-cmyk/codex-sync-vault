# -*- coding: utf-8 -*-
"""Adobe Premiere 标准流程清单 — 交付前逐项勾选"""
CHECKS = [
  "序列规格(分辨率帧率)正确",
  "剪辑点与节奏合理",
  "字幕准确",
  "色调统一",
  "音画同步音量平衡",
  "导出编码匹配平台/硬件"
]
def main():
    print(f"{'='*46}\n  Adobe Premiere 交付前自检清单\n{'='*46}")
    ok = True
    for i, c in enumerate(CHECKS, 1):
        print(f"  [ ] {i}. {c}")
    print("\n逐项完成后，把成功案例写回经验库 experience-base.md。")
if __name__ == "__main__":
    main()
