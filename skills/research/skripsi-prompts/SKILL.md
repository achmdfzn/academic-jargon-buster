---
name: skripsi-prompts
description: "Ready-made prompt templates for writing a thesis (skripsi), from research roadmap to defense prep and publication."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Academic, Thesis, Writing, Prompts, Indonesian]
    related_skills: [academic-jargon-buster, citation-weaver, academic-writing, write-academic-id]
---

## Verification Hierarchy

**Always verify before claiming skripsi-prompts capability.**

1. **llms.txt index** — <https://hermes-agent.nousresearch.com/docs/llms.txt> — the entire docs set in one file. Query first.
2. **CLI reference** — `hermes --help`, `hermes skripsi-prompts --help` — command-level truth.
3. **Source tree** — <https://github.com/NousResearch/hermes-agent> — upstream changes, issues, PRs.
4. **This skill body** — what's documented here; treat as per-session context, not product gospel.

Never claim a skripsi-prompts feature you haven't verified. When in doubt, fetch `llms.txt` and search. If it's not there, check the source. If it's not in source either, mark as UNKNOWN.

## Professional Operating Standards

- **Verify before assertion** — never claim a skripsi-prompts feature you haven't executed.
- **Output over process narration** — report what changed and what's verified, not the steps taken.
- **Fail with evidence** — on a blocker, paste the exact error and say what you tried, then stop or escalate.
- **Coordinate first, spawn second** — prefer in-session tools (`delegate_task`, `cronjob`) before long-lived processes.
- **Ops discipline** — one operation per batch call; atomic results; roll back on failure.
- **Version everything** — bump `version` in frontmatter when behavior changes; keep metadata accurate.

# Skripsi Prompts Skill

Ready-made prompt templates for writing a thesis (skripsi) in Indonesian. One template per task: research roadmap, each chapter (Bab 1–5), defense preparation, and publication. The student picks a template, fills its placeholders with their own title, theory, method, and data, then pastes the result into the recommended AI tool (ChatGPT, Grok, Claude, Gemini, Perplexity, Manus).

The templates below are the same ones in `academic_tools.py` (`PROMPTS`). Keep them in sync: if a template changes in one place, change it in the other.

## Rules (non-negotiable)

- **These prompts help the student write their own thesis. They never write a whole thesis for the student.** Guide structure, help fill placeholders from the student's own notes, explain the rules. Do not produce a complete chapter, thesis, or journal article on the student's behalf.
- **Never invent a reference, a data point, or a source.** A missing reference stays missing. If the student has no data for a placeholder, say so and stop — do not guess.
- **Placeholders come from the student.** Ask for the title, theory, method, variables, and data. Never fill them with invented values.
- **The student runs the prompt.** The filled prompt is the deliverable; the student pastes it into the recommended AI tool themselves.

## The 15 prompts

### 1. `roadmap` — Roadmap Penelitian (Persiapan, ChatGPT)

Placeholders: judul, teori, metode, bulan, tanggal.

> Saya sedang mengerjakan skripsi berjudul {judul}, memakai teori {teori} dan metode {metode}. Bantu saya menyusun rencana kerja penelitian dari awal sampai selesai: mulai dari merumuskan masalah, membaca literatur, menyiapkan instrumen, mengumpulkan data, menganalisis, hingga menulis laporan dan menyiapkan publikasi. Waktu yang saya punya {bulan} bulan, mulai {tanggal}. Tuliskan sebagai daftar langkah berurutan dengan perkiraan durasi tiap langkahnya.

### 2. `latar-belakang` — Latar Belakang, Bab 1 (Grok)

Placeholders: topik, catatan, paragraf.

> Saya sedang menulis bagian latar belakang untuk skripsi bertopik {topik}. Berikut poin-poin dari saya dan dosen pembimbing: {catatan}. Tolong rangkai poin-poin itu menjadi latar belakang yang runtut dengan struktur piramida terbalik, dari isu umum ke konteks lokal, lalu ke masalah spesifik penelitian saya. Sertakan data atau referensi pendukung bila ada, gunakan bahasa akademik standar skripsi, dan buat dalam {paragraf} paragraf yang mengalir dan siap dipakai di dokumen skripsi.

### 3. `banding-teori` — Membandingkan 3 Teori, Bab 2 (Grok)

Placeholders: judul.

> Saya sedang menulis skripsi tentang {judul}. Tolong carikan tiga teori yang relevan dengan topik ini, lalu bandingkan ketiganya dalam tabel: nama teori, tokoh atau penelitinya, konsep utama, kelebihan dan keterbatasan, serta relevansinya dengan penelitian saya. Di akhir, beri rekomendasi teori mana yang paling cocok dijadikan landasan teori penelitian saya.

### 4. `review-terdahulu` — Review Penelitian Terdahulu, Bab 2 (Grok)

Placeholders: judul, daftar, gaya.

> Saya sedang meneliti {judul}. Berikut daftar penelitian terdahulu yang saya jadikan rujukan: {daftar}. Tolong buat ulasan kritis terhadap penelitian-penelitian itu, dengan fokus pada metode, sampel, hasil, dan keterbatasannya. Jelaskan celah penelitian (research gap) yang belum banyak diteliti dan bagaimana penelitian saya bisa mengisinya. Tulis dalam bahasa akademik, sekitar 3-4 paragraf, dengan sitasi gaya {gaya}.

### 5. `metodologi` — Metodologi Penelitian, Bab 3 (ChatGPT)

Placeholders: judul, jenis, metode, populasi, pengumpulan, analisis.

> Saya sedang menulis Bab 3 Metodologi Penelitian untuk skripsi berjudul {judul}. Jenis penelitian saya: {jenis}. Metode yang digunakan: {metode}. Populasi dan sampel: {populasi}. Teknik pengumpulan data: {pengumpulan}. Teknik analisis data: {analisis}. Susunlah Bab 3 yang lengkap dan logis, mencakup desain penelitian, definisi operasional variabel, populasi dan sampel, instrumen penelitian, teknik pengumpulan data, dan teknik analisis data. Pastikan isinya selaras dengan judul serta Bab 1 dan 2, dan jelaskan alasan metode ini paling tepat untuk penelitian saya, dengan bahasa akademik yang rapi.

### 6. `hubungan-variabel` — Hubungan Antar Variabel, Bab 3 (ChatGPT / Grok)

Placeholders: judul, variabel_x, variabel_y, variabel_z.

> Saya sedang menulis Bab 3 skripsi berjudul {judul}. Variabel penelitian saya: variabel X = {variabel_x}, variabel Y = {variabel_y}, variabel Z = {variabel_z} (bila ada). Tolong buat paragraf yang menjelaskan hubungan antar variabel ini berdasarkan teori yang relevan. Uraikan secara runtut, mulai dari hubungan X ke Y, lalu Z bila ada. Jelaskan mengapa hubungan ini penting untuk diteliti, dan dukung dengan minimal 3 referensi dari penelitian terdahulu (format APA 7th).

### 7. `hipotesis` — Perkiraan Hipotesis, Bab 3 (Grok)

Placeholders: judul, variabel.

> Saya sedang menyusun hipotesis untuk skripsi berjudul {judul}. Variabel yang saya teliti: {variabel}. Tolong carikan minimal 5 penelitian terdahulu yang meneliti hubungan serupa. Ringkas temuan utama masing-masing penelitian, lalu susun hipotesis yang logis dan bisa diuji. Format hasilnya: ringkasan penelitian terdahulu (penulis, tahun, temuan, relevansi), sintesis hubungan antar penelitian (pola, konsistensi, atau perdebatan yang ada), dan hipotesis saya (H0, H1, dst) dalam format yang jelas dan siap dimasukkan ke Bab 3.

### 8. `mixed-methods` — Analisis Mixed-Methods, Bab 4 (ChatGPT)

Placeholders: judul, kuantitatif, kualitatif.

> Saya sedang menganalisis data penelitian mixed method untuk skripsi berjudul {judul}. Metode kuantitatif saya: {kuantitatif}. Metode kualitatif saya: {kualitatif}. Saya akan melampirkan file data mentah saya. Tolong analisis dengan langkah: (1) Analisis kuantitatif: bersihkan data dan jelaskan penanganan missing value, lakukan uji statistik yang sesuai, sajikan hasil dalam tabel beserta interpretasi (p-value, signifikansi, effect size), dan buat visualisasi sederhana bila relevan. (2) Analisis kualitatif: lakukan coding tematik, sajikan tema utama beserta kutipan perwakilan responden, dan interpretasikan maknanya. (3) Integrasi: gabungkan kedua hasil, tunjukkan apakah keduanya saling mendukung, melengkapi, atau bertentangan, dan buat kesimpulan sementara yang menjawab rumusan masalah. Gunakan bahasa akademik yang jelas dan sistematis, dengan format akhir yang siap dimasukkan ke Bab 4.

### 9. `saran` — Saran Penelitian, Bab 5 (ChatGPT)

Placeholders: judul, hasil.

> Saya sedang menyusun Bab 5 skripsi berjudul {judul}. Berdasarkan hasil penelitian saya berikut: {hasil}, tolong buatkan saran penelitian yang konstruktif untuk tiga pihak: (1) praktisi atau industri, (2) akademisi, dan (3) peneliti berikutnya. Tulis dengan bahasa akademik, masing-masing satu paragraf, dan pastikan setiap saran bisa diterapkan dan relevan dengan temuan penelitian saya.

### 10. `keterbatasan` — Keterbatasan + Peluang Penelitian, Bab 5 (ChatGPT)

Placeholders: judul, metode, data.

> Saya sedang menulis Bab 5 skripsi berjudul {judul}. Metode penelitian saya: {metode}, dengan data: {data}. Tolong buatkan bagian keterbatasan penelitian yang ditulis secara elegan dan profesional, tanpa melemahkan hasil penelitian, lalu lanjutkan dengan peluang penelitian lanjutan. Berikan 3-5 ide penelitian berikutnya yang relevan, misalnya metode baru, populasi berbeda, atau variabel tambahan, dan jelaskan mengapa setiap ide penting untuk dikaji.

### 11. `review-draf` — Review Draf Skripsi, Persiapan Sidang (Claude / Manus)

Placeholders: none (the student attaches their thesis file).

> Saya akan melampirkan file skripsi saya (PDF/DOC). Tolong baca dan analisis seluruh isinya, dan berperan sebagai dosen pembimbing sekaligus dosen penguji yang objektif dan kritis. Beri masukan tentang bagian yang masih lemah, berpotensi jadi revisi, atau bisa memicu pertanyaan saat seminar dan sidang. Jelaskan secara spesifik letak masalahnya (bab atau subbab), alasan bagian itu dinilai kurang kuat, dan aspek apa yang sebaiknya diperdalam, tanpa langsung menuliskan revisinya. Sebutkan juga kekuatan skripsi saya, dari argumentasi, teori, metodologi, analisis, sampai kebaruan penelitian. Terakhir, evaluasi aspek teknis penulisan: sistematika, alur antarparagraf, konsistensi istilah, kualitas sitasi dan daftar pustaka, format tabel atau gambar, serta potensi kesalahan akademik lainnya. Sajikan evaluasi dalam kategori yang jelas, diurutkan berdasarkan prioritas (tinggi, sedang, rendah), agar saya tahu bagian mana yang harus diperbaiki dulu.

### 12. `ppt` — Skripsi Menjadi PowerPoint, Persiapan Sidang (ChatGPT)

Placeholders: judul, jumlah_slide.

> Saya ingin mengubah skripsi saya berjudul {judul} menjadi slide presentasi PowerPoint. Saya akan melampirkan file skripsinya. Tolong rangkum setiap bab menjadi slide dengan judul yang singkat dan menarik. Isi tiap slide berupa poin-poin penting (maksimal 5 poin per slide), ditambah 1-2 kalimat penjelas untuk setiap slide agar saya tahu apa yang harus diucapkan. Ikuti struktur presentasi skripsi: latar belakang, rumusan masalah, tujuan, tinjauan pustaka, metode, hasil, pembahasan, kesimpulan, dan saran. Bila perlu, rekomendasikan grafik, tabel, atau diagram untuk memperjelas. Hasil akhirnya adalah presentasi sebanyak {jumlah_slide} slide yang siap dipakai tanpa banyak edit.

### 13. `cue-card` — Cue Card Presentasi, Persiapan Sidang (ChatGPT)

Placeholders: none (follows the PPT from prompt 12).

> Tolong buatkan cue card singkat dan padat untuk membantu saya saat presentasi skripsi. Bagi per slide sesuai urutan PPT skripsi saya. Tulis poin-poin atau kalimat kunci yang harus saya ucapkan, dengan bahasa lisan yang natural tapi tetap profesional. Jangan terlalu panjang, cukup 2-3 kalimat per slide supaya mudah dihafalkan. Tambahkan tips intonasi atau gestur (misalnya: senyum di awal, lihat audiens saat menyebut hasil utama). Pastikan cue card ini membuat saya percaya diri, tidak terdengar kaku, dan membantu menjawab kemungkinan pertanyaan dari penguji.

### 14. `blog` — Skripsi Menjadi Artikel Blog, Publikasi (ChatGPT)

Placeholders: judul, platform, kata.

> Saya ingin mengubah skripsi saya berjudul {judul} menjadi artikel pendek yang siap dipublikasikan di {platform}. Saya akan melampirkan file skripsinya. Tolong ambil intisarinya lalu tulis ulang dengan bahasa yang santai, mudah dipahami pembaca awam, dan tetap menarik. Panjang artikel sekitar {kata} kata. Susun dengan struktur yang runtut: mulai dari pembuka yang menarik perhatian (fakta menarik, pertanyaan, atau fenomena terkini), lalu paparkan masalah yang saya teliti dan relevansinya, jelaskan metode dan temuan utama secara singkat tanpa terlalu banyak jargon, dan tutup dengan manfaat praktis penelitian ini bagi pembaca. Bila perlu, tambahkan statistik, contoh kasus, atau call-to-action, dan pastikan artikel mencantumkan kredit ke penelitian saya agar bisa dipakai sebagai portofolio.

### 15. `jurnal` — Skripsi Menjadi Artikel Jurnal, Publikasi (ChatGPT)

Placeholders: bagian, jumlah.

> Saya ingin memublikasikan jurnal berdasarkan skripsi saya. Ini bagian yang perlu dirangkum menjadi paragraf yang lebih singkat untuk jurnal saya: {bagian}. Buatkan maksimal sebanyak {jumlah} paragraf atau kata. Pertahankan sitasinya dan jangan membuang inti tiap paragraf. Gunakan bahasa yang humanis dan tidak terkesan robotik. Hindari kata yang berulang dan struktur kalimat yang generik, variasikan panjang kalimat, dan hindari em-dash dan titik koma. Berikut paragraf yang perlu dipersingkat: [tempel paragraf kamu di sini, satu bagian saja].

## Usage

```bash
python3 academic_tools.py prompts --list
python3 academic_tools.py prompts latar-belakang
python3 academic_tools.py prompts roadmap --set judul="..." --set teori="..." --set metode="..." --set bulan=6 --set tanggal="11 November 2026"
```

Or open the interactive menu (`python3 academic_tools.py`) and pick option 3, Prompt Skripsi.
