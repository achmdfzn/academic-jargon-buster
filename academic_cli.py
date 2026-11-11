#!/usr/bin/env python3
"""Academic CLI — one interactive command for both skills in this repo.

Like the Claude CLI: run one command, then pick what to do from a menu.

    python3 academic_cli.py              # interactive menu (default)
    python3 academic_cli.py jargon ...   # straight to Jargon Buster
    python3 academic_cli.py cite ...     # straight to Citation Weaver

Interactive menu (bilingual — Indonesian / English):

    ================= Academic Tools =================
    1. Jargon Buster    — terjemahkan istilah akademik / translate jargon
    2. Citation Weaver  — sisipkan sitasi ke naskah / weave citations
    3. Ganti bahasa     — switch language (id/en)
    0. Keluar           — exit

Inside each tool there are more choices: type text or read a file, pick a
field / citation style / major, and pick the output language. Everything is
plain input() prompts — no extra dependencies, works over SSH too.

Both tools keep their own standalone CLIs (jargon_buster.py and
citation_weaver.py) for scripting; this file only wraps them in a menu.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import citation_weaver as cw
import jargon_buster as jb

__version__ = "1.0.0"

DEFAULT_REFS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "demos", "citation-weaver", "references.json",
)

STRINGS = {
    "id": {
        "banner": "Academic Tools — Jargon Buster + Citation Weaver",
        "menu_title": "Pilih alat:",
        "jargon": "Jargon Buster — terjemahkan istilah akademik",
        "cite": "Citation Weaver — sisipkan sitasi ke naskah",
        "lang": "Ganti bahasa (id/en)",
        "exit": "Keluar",
        "back": "Kembali",
        "choice": "Pilihanmu",
        "invalid": "Pilihan tidak dikenal, coba lagi.",
        "goodbye": "Sampai jumpa!",
        "type_text": "Ketik teks (baris kosong = selesai):",
        "read_file": "Baca dari file",
        "file_path": "Path file",
        "file_missing": "File tidak ditemukan:",
        "field": "Bidang (kosong = semua bidang)",
        "format": "Format output: 1 = Markdown, 2 = CSV",
        "list_terms": "Lihat kamus",
        "add_terms": "Tambah istilah dari file JSON",
        "json_path": "Path file JSON",
        "added": "Istilah ditambahkan:",
        "refs": "File bibliografi JSON (kosong = contoh bawaan)",
        "refs_missing": "File bibliografi tidak ditemukan:",
        "pick_style": "Pilih gaya sitasi:",
        "pick_major": "Pilih jurusan (rekomendasi gaya otomatis):",
        "by_major": "Pilih dari jurusan",
        "out_lang": "Bahasa output: 1 = Indonesia, 2 = English",
        "list_styles": "Lihat gaya sitasi",
        "list_majors": "Lihat jurusan",
        "press_enter": "Tekan Enter untuk kembali...",
        "result": "Hasil:",
    },
    "en": {
        "banner": "Academic Tools — Jargon Buster + Citation Weaver",
        "menu_title": "Choose a tool:",
        "jargon": "Jargon Buster — translate academic jargon",
        "cite": "Citation Weaver — weave citations into text",
        "lang": "Switch language (id/en)",
        "exit": "Exit",
        "back": "Back",
        "choice": "Your choice",
        "invalid": "Unknown choice, try again.",
        "goodbye": "Goodbye!",
        "type_text": "Type text (empty line = done):",
        "read_file": "Read from file",
        "file_path": "File path",
        "file_missing": "File not found:",
        "field": "Field (empty = all fields)",
        "format": "Output format: 1 = Markdown, 2 = CSV",
        "list_terms": "List dictionary terms",
        "add_terms": "Add terms from a JSON file",
        "json_path": "JSON file path",
        "added": "Terms added:",
        "refs": "Bibliography JSON file (empty = bundled sample)",
        "refs_missing": "Bibliography file not found:",
        "pick_style": "Pick a citation style:",
        "pick_major": "Pick a major (recommended style is automatic):",
        "by_major": "Pick from major",
        "out_lang": "Output language: 1 = Indonesian, 2 = English",
        "list_styles": "List citation styles",
        "list_majors": "List majors",
        "press_enter": "Press Enter to go back...",
        "result": "Result:",
    },
}


class CLI:
    """Interactive menu session. `lang` is the UI language (id/en)."""

    def __init__(self, lang: str = "id"):
        self.lang = lang if lang in STRINGS else "id"

    @property
    def t(self):
        return STRINGS[self.lang]

    def ask(self, prompt: str, default: str = "") -> str:
        """One line of input; returns default on empty line, '' on EOF."""
        try:
            answer = input(f"{prompt} " if not default else f"{prompt} [{default}] ")
        except (EOFError, KeyboardInterrupt):
            print()
            return ""
        return answer.strip() or default

    def ask_choice(self, prompt: str, count: int) -> int | None:
        """Ask for a number 0..count.

        Returns None on empty line/EOF (means: back/exit), -1 on an
        invalid number (caller should re-prompt, not quit).
        """
        raw = self.ask(f"{prompt} (0-{count})")
        if not raw:
            return None
        try:
            n = int(raw)
        except ValueError:
            print(self.t["invalid"])
            return -1
        if 0 <= n <= count:
            return n
        print(self.t["invalid"])
        return -1

    def pause(self):
        try:
            input(f"\n{self.t['press_enter']}")
        except (EOFError, KeyboardInterrupt):
            print()

    def read_text(self) -> str | None:
        """Choice: type multi-line text, or read from a file."""
        print(f"  1. {self.t['type_text'].split(' (')[0]}")
        print(f"  2. {self.t['read_file']}")
        print(f"  0. {self.t['back']}")
        choice = self.ask_choice(self.t["choice"], 2)
        if choice == 1:
            print(self.t["type_text"])
            lines = []
            try:
                while True:
                    line = input()
                    if not line.strip():
                        break
                    lines.append(line)
            except (EOFError, KeyboardInterrupt):
                print()
            return "\n".join(lines)
        if choice == 2:
            path = self.ask(self.t["file_path"])
            if not path:
                return None
            if not os.path.isfile(path):
                print(f"{self.t['file_missing']} {path}")
                return None
            with open(path, encoding="utf-8") as f:
                return f.read()
        return None

    # -- main menu ------------------------------------------------------

    def run(self) -> int:
        while True:
            print(f"\n{'=' * 20} {self.t['banner']} {'=' * 20}")
            print(self.t["menu_title"])
            print(f"1. {self.t['jargon']}")
            print(f"2. {self.t['cite']}")
            print(f"3. {self.t['lang']}")
            print(f"0. {self.t['exit']}")
            choice = self.ask_choice(self.t["choice"], 3)
            if choice == -1:
                continue
            if choice == 1:
                self.jargon_menu()
            elif choice == 2:
                self.cite_menu()
            elif choice == 3:
                self.lang = "en" if self.lang == "id" else "id"
            elif choice == 0 or choice is None:
                print(self.t["goodbye"])
                return 0

    # -- Jargon Buster --------------------------------------------------

    def jargon_menu(self):
        while True:
            print(f"\n--- {self.t['jargon']} ---")
            print(f"1. {self.t['type_text'].split(' (')[0]} / {self.t['read_file']}")
            print(f"2. {self.t['list_terms']}")
            print(f"3. {self.t['add_terms']}")
            print(f"0. {self.t['back']}")
            choice = self.ask_choice(self.t["choice"], 3)
            if choice == -1:
                continue
            if choice == 1:
                self.jargon_annotate()
            elif choice == 2:
                field = self.ask(self.t["field"])
                for item in jb.list_terms(field or None):
                    print(f"- {item['term']} ({item['field']}): {item['translation']}")
                self.pause()
            elif choice == 3:
                path = self.ask(self.t["json_path"])
                if path and os.path.isfile(path):
                    added = jb.update_dictionary(path)
                    print(f"{self.t['added']} {', '.join(added) if added else '-'}")
                elif path:
                    print(f"{self.t['file_missing']} {path}")
                self.pause()
            elif choice == 0 or choice is None:
                return

    def jargon_annotate(self):
        text = self.read_text()
        if not text:
            return
        field = self.ask(self.t["field"])
        print(f"1. Markdown\n2. CSV")
        fmt = self.ask_choice(self.t["format"], 2)
        if fmt == 2:
            out = jb.to_csv(text, field or None)
        else:
            out = jb.to_annotated_markdown(text, field or None)
        print(f"\n{self.t['result']}\n{out}")
        self.pause()

    # -- Citation Weaver ------------------------------------------------

    def cite_menu(self):
        while True:
            print(f"\n--- {self.t['cite']} ---")
            print(f"1. {self.t['type_text'].split(' (')[0]} / {self.t['read_file']}")
            print(f"2. {self.t['list_styles']}")
            print(f"3. {self.t['list_majors']}")
            print(f"0. {self.t['back']}")
            choice = self.ask_choice(self.t["choice"], 3)
            if choice == -1:
                continue
            if choice == 1:
                self.cite_weave()
            elif choice == 2:
                for i, s in enumerate(cw.STYLES, 1):
                    print(f"  {i}. {s}")
                self.pause()
            elif choice == 3:
                for i, d in enumerate(cw.DISCIPLINES, 1):
                    print(f"  {i}. {d['id']} / {d['en']} -> {d['style']}")
                self.pause()
            elif choice == 0 or choice is None:
                return

    def pick_style(self) -> str | None:
        print(f"\n{self.t['pick_style']}")
        for i, s in enumerate(cw.STYLES, 1):
            print(f"  {i}. {s}")
        print(f"  {len(cw.STYLES) + 1}. {self.t['by_major']}")
        choice = self.ask_choice(self.t["choice"], len(cw.STYLES) + 1)
        if choice is None or choice == 0:
            return None
        if choice == len(cw.STYLES) + 1:
            return self.pick_style_by_major()
        return cw.STYLES[choice - 1]

    def pick_style_by_major(self) -> str | None:
        print(f"\n{self.t['pick_major']}")
        for i, d in enumerate(cw.DISCIPLINES, 1):
            print(f"  {i}. {d['id']} / {d['en']} -> {d['style']}")
        choice = self.ask_choice(self.t["choice"], len(cw.DISCIPLINES))
        if choice is None or choice == 0:
            return None
        return cw.DISCIPLINES[choice - 1]["style"]

    def cite_weave(self):
        text = self.read_text()
        if not text:
            return
        refs_path = self.ask(self.t["refs"], DEFAULT_REFS)
        if not os.path.isfile(refs_path):
            print(f"{self.t['refs_missing']} {refs_path}")
            return
        style = self.pick_style()
        if not style:
            return
        print("1. Indonesia\n2. English")
        lang_choice = self.ask_choice(self.t["out_lang"], 2)
        lang = "en" if lang_choice == 2 else "id"
        refs = cw.load_references(refs_path)
        out = cw.weave(text, refs, style=style, lang=lang)
        print(f"\n{self.t['result']}\n{out}")
        self.pause()


def main(argv=None) -> int:
    """Entry point. No args -> interactive menu; jargon/cite -> passthrough."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("jargon", "cite"):
        tool, rest = argv[0], argv[1:]
        return jb.main(rest) if tool == "jargon" else cw.main(rest)
    if argv and argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv and argv[0] in ("-v", "--version"):
        print(f"academic_cli {__version__} "
              f"(jargon_buster {jb.__version__}, citation_weaver {cw.__version__})")
        return 0
    try:
        return CLI().run()
    except (EOFError, KeyboardInterrupt):
        print()
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
