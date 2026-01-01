# merge_pngs_to_pdf_bookmarks.py
from __future__ import annotations

import io
import tempfile
from pathlib import Path

import img2pdf
import pikepdf
from natsort import natsorted
from PIL import Image


def optimize_png_lossless(img_path: Path) -> bytes:
    """无损优化PNG图片，返回优化后的字节数据"""
    with Image.open(img_path) as img:
        # 保持原有模式（RGBA/RGB/P等）
        buffer = io.BytesIO()
        # compress_level=9 是PNG最高压缩级别（无损）
        # optimize=True 启用额外优化
        img.save(buffer, format="PNG", compress_level=9, optimize=True)
        return buffer.getvalue()


def main() -> None:
    # 以脚本所在的**文件夹**为准（把脚本放在**PNG图片**同一**文件夹**）
    folder = Path(__file__).resolve().parent

    # 收集所有**PNG图片**
    pngs = [p for p in folder.glob("*.png") if p.is_file()]
    pngs = natsorted(pngs)  # 自然排序：1,2,10 而不是 1,10,2

    if not pngs:
        raise SystemExit("未找到任何 .png **图片文件**")

    # 输出**PDF文件名**（以文件夹名称命名）
    out_pdf = folder / f"{folder.name}.pdf"

    # 1) 无损优化PNG并生成临时PDF
    print("正在优化图片（无损压缩）...")
    optimized_images = []
    original_size = 0
    optimized_size = 0

    for png in pngs:
        original_size += png.stat().st_size
        optimized_data = optimize_png_lossless(png)
        optimized_size += len(optimized_data)
        optimized_images.append(optimized_data)

    print(f"原始大小：{original_size / 1024 / 1024:.2f} MB")
    print(f"优化后大小：{optimized_size / 1024 / 1024:.2f} MB")
    print(f"压缩率：{(1 - optimized_size / original_size) * 100:.1f}%")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(img2pdf.convert(optimized_images))
        tmp_path = Path(tmp.name)

    # 2) 添加**书签**（标题=**原文件名**，跳转到对应**页面**）
    print("正在添加书签...")
    with pikepdf.open(tmp_path) as pdf:
        with pdf.open_outline() as outline:
            used_titles: dict[str, int] = {}
            for i, img_path in enumerate(pngs):
                title = img_path.stem  # **原文件名**（不含扩展名）

                # 防止**重名文件**导致**书签**重复
                if title in used_titles:
                    used_titles[title] += 1
                    title = f"{title} ({used_titles[title]})"
                else:
                    used_titles[title] = 1

                # 创建指向第 i 页的目标（页面顶部，适合窗口宽度）
                dest = pikepdf.make_page_destination(pdf, i, "FitH")
                # 创建书签条目
                item = pikepdf.OutlineItem(title, dest)
                outline.root.append(item)

        # 保存时启用对象流压缩
        pdf.save(out_pdf, object_stream_mode=pikepdf.ObjectStreamMode.generate)

    # 3) 删除临时文件
    tmp_path.unlink()

    final_size = out_pdf.stat().st_size
    print(f"\n已生成（带书签）：{out_pdf.name}")
    print(f"最终PDF大小：{final_size / 1024 / 1024:.2f} MB")
    print(f"包含图片数量：{len(pngs)}")
    print(f"来源文件夹：{folder}")


if __name__ == "__main__":
    main()
