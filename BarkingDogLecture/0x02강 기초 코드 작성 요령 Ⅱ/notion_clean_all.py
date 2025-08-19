import re, os, shutil
from pathlib import Path
from urllib.parse import unquote, quote

HEX32 = re.compile(r"[0-9a-f]{32}$", re.I)
LECTURE_NUM = re.compile(r"0x(\d+)\s*강", re.I)  # "0x01강" -> "01"

def strip_hash(name: str) -> str:
    parts = name.split()
    if parts and HEX32.fullmatch(parts[-1] or ""):
        return " ".join(parts[:-1]).rstrip(" |_")
    return name

def remove_brackets(s: str) -> str:
    return s.replace("[", "").replace("]", "").strip()

def extract_number(title: str, fallback_idx: int) -> str:
    m = LECTURE_NUM.search(title)
    if m:
        return m.group(1).zfill(2)
    return str(fallback_idx).zfill(2)

def rename_folder(src: Path, dst: Path):
    if src.resolve() == dst.resolve():
        return
    if dst.exists():
        for p in src.iterdir():
            t = dst / p.name
            if p.is_dir():
                t.mkdir(exist_ok=True)
                rename_folder(p, t)
            else:
                if not t.exists():
                    shutil.move(str(p), str(t))
        src.rmdir()
    else:
        shutil.move(str(src), str(dst))

def find_md_for_folder(parent: Path, folder_name: str) -> Path | None:
    cands = list(parent.glob("*.md"))
    if not cands: return None

    def norm(x: str) -> str:
        return remove_brackets(strip_hash(x))

    target = norm(folder_name)
    for p in cands:
        if norm(p.stem) == target:
            return p
    for p in cands:
        if folder_name in p.stem or HEX32.search(p.stem):
            return p
    if len(cands) == 1:
        return cands[0]
    return None

def replace_links(md_path: Path, old_dirnames: list[str], new_img_dir_abs: Path):
    text = md_path.read_text(encoding="utf-8")
    md_dir = md_path.parent

    # md에서 new_img_dir까지의 상대경로 계산 (일반적으로 "lecture 01")
    rel_to_imgs = Path(os.path.relpath(new_img_dir_abs, md_dir)).as_posix()

    def rewrite_path(orig_path: str) -> str:
        dec = unquote(orig_path)
        # old_dirnames 중 하나가 포함되어 있으면 교체 대상
        if not any(od in orig_path or od in dec for od in old_dirnames):
            return orig_path

        p = Path(dec)
        parts = list(p.parts)
        if not parts:
            return orig_path

        # 첫 디렉터리를 새 폴더명으로 강제 교체
        new_parts = [rel_to_imgs] + parts[1:]
        new_path = "/".join(new_parts)

        # 공백/한글 등 URL 인코딩 (슬래시/점/밑줄/대시/괄호는 유지)
        encoded = quote(new_path, safe="/:._-()")
        return encoded

    def repl(m):
        path = m.group(1)
        return m.group(0).replace(path, rewrite_path(path))

    pats = [
        re.compile(r"!\[[^\]]*\]\(([^)]+)\)"),       # 이미지
        re.compile(r"(?<!\!)\[[^\]]*\]\(([^)]+)\)"), # 일반 링크
    ]
    for pat in pats:
        text = pat.sub(repl, text)

    # 백업 후 저장
    bak = md_path.with_suffix(md_path.suffix + ".bak")
    bak.write_text(md_path.read_text(encoding="utf-8"), encoding="utf-8")
    md_path.write_text(text, encoding="utf-8")

    # 간단한 존재 검사 (경고 출력)
    missing = []
    for m in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", text):
        link = unquote(m.group(1))
        target = (md_dir / link).resolve()
        if not target.exists():
            missing.append(link)
    if missing:
        print(f"⚠️  {md_path.name} 에서 누락된 이미지 경로 {len(missing)}개:")
        for s in missing[:10]:
            print("   -", s)
        if len(missing) > 10:
            print("   ...")

def process_one(parent: Path, folder: Path, order_idx: int) -> bool:
    old_dir = folder.name
    base_dir = strip_hash(old_dir)
    pretty_title = remove_brackets(base_dir)
    num = extract_number(pretty_title, order_idx)
    new_img_dir_name = f"lecture {num}"
    new_img_dir_abs = parent / new_img_dir_name

    md = find_md_for_folder(parent, old_dir)
    if not md:
        print(f"⚠️  {old_dir} 대응 .md를 못 찾음 (건너뜀)")
        return False

    # 이미지 폴더명 변경
    rename_folder(folder, new_img_dir_abs)

    # .md 내부 링크 전부 교체
    old_variants = list({
        old_dir, base_dir, pretty_title,
        unquote(old_dir), unquote(base_dir), unquote(pretty_title),
    })
    replace_links(md, sorted(old_variants, key=len, reverse=True), new_img_dir_abs)

    # .md 파일명: 해시/대괄호 제거
    clean_md_name = remove_brackets(strip_hash(md.stem)) + md.suffix
    desired = parent / clean_md_name
    if md.resolve() != desired.resolve():
        if desired.exists():
            desired.with_suffix(".md.bak").write_text(desired.read_text(encoding="utf-8"), encoding="utf-8")
        shutil.move(str(md), str(desired))
    return True

def main():
    root = Path(".").resolve()
    folders = [p for p in sorted(root.iterdir())
               if p.is_dir() and HEX32.search(p.name or "")]
    count = 0
    for idx, folder in enumerate(folders, start=1):
        if process_one(root, folder, idx):
            count += 1
    print(f"\n완료 ✅ {count}개 정리됨")
    print(" - 이미지 폴더: 'lecture 01', 'lecture 02', ...")
    print(" - .md: 해시/대괄호 제거, 링크는 상대경로 + 공백 인코딩(%20)")
    print(" - 누락 경로 경고가 나오면, 해당 파일이 폴더에 실제로 있는지 확인하세요.")

if __name__ == "__main__":
    main()
