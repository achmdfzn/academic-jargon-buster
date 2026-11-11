---
name: skripsi-prompts
description: "Ready-made prompt templates for writing a thesis (skripsi), from research roadmap to defense prep and publication."
version: 1.1.0
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

Ready-made prompt templates for writing a thesis (skripsi) in Indonesian and English. One template per task: research roadmap, abstract, preface, problem statement, each chapter (Bab 1–5), defense preparation, and publication. Every template has an Indonesian and an English version with the same placeholders. The student picks a template, fills its placeholders with their own title, theory, method, and data, then pastes the result into the recommended AI tool (ChatGPT, Grok, Claude, Gemini, Perplexity, Manus).

The templates below are the same ones in `academic_tools.py` (`PROMPTS`). Keep them in sync: if a template changes in one place, change it in the other.

## Rules (non-negotiable)

- **These prompts help the student write their own thesis. They never write a whole thesis for the student.** Guide structure, help fill placeholders from the student's own notes, explain the rules. Do not produce a complete chapter, thesis, or journal article on the student's behalf.
- **Never invent a reference, a data point, or a source.** A missing reference stays missing. If the student has no data for a placeholder, say so and stop — do not guess.
- **Placeholders come from the student.** Ask for the title, theory, method, variables, and data. Never fill them with invented values.
- **The student runs the prompt.** The filled prompt is the deliverable; the student pastes it into the recommended AI tool themselves.

## The 18 prompts

### 1. `roadmap` — Roadmap Penelitian (Persiapan, ChatGPT)

Placeholders: judul, teori, metode, bulan, tanggal.

> Saya sedang mengerjakan skripsi berjudul {judul}, memakai teori {teori} dan metode {metode}. Bantu saya menyusun rencana kerja penelitian dari awal sampai selesai: mulai dari merumuskan masalah, membaca literatur, menyiapkan instrumen, mengumpulkan data, menganalisis, hingga menulis laporan dan menyiapkan publikasi. Waktu yang saya punya {bulan} bulan, mulai {tanggal}. Tuliskan sebagai daftar langkah berurutan dengan perkiraan durasi tiap langkahnya.

English:

> I am working on a thesis titled {judul}, using {teori} theory and the {metode} method. Help me build a work plan for the research from start to finish: from formulating the problem, reading the literature, preparing instruments, collecting data, analyzing, to writing the report and preparing publication. I have {bulan} months, starting {tanggal}. Write it as an ordered list of steps with an estimated duration for each step.

### 2. `abstrak` — Abstrak Skripsi (Abstrak, ChatGPT)

Placeholders: judul, masalah, metode, hasil, kunci.

> Saya sedang menulis abstrak skripsi berjudul {judul}. Masalah yang saya teliti: {masalah}. Metode yang saya pakai: {metode}. Hasil utama penelitian saya: {hasil}. Tolong susun abstrak dalam satu paragraf (sekitar 150-250 kata) dengan struktur: latar belakang singkat, tujuan, metode, hasil utama, dan kesimpulan. Akhiri dengan kata kunci: {kunci}. Gunakan bahasa akademik yang ringkas dan jelas, tanpa menambahkan data atau klaim yang tidak saya sebutkan.

English:

> I am writing the abstract for my thesis titled {judul}. The problem I studied: {masalah}. The method I used: {metode}. My main findings: {hasil}. Please draft the abstract as a single paragraph (about 150-250 words) with this structure: brief background, objective, method, main findings, and conclusion. End with keywords: {kunci}. Use concise, clear academic language, and do not add any data or claims I did not mention.

### 3. `kata-pengantar` — Kata Pengantar (Persiapan, ChatGPT)

Placeholders: judul, pembimbing, ucapan.

> Saya sedang menulis kata pengantar skripsi berjudul {judul}, dibimbing oleh {pembimbing}. Pihak-pihak yang ingin saya ucapkan terima kasih: {ucapan}. Tolong susun kata pengantar yang sopan dan formal: buka dengan puji syukur, sebutkan judul skripsi dan tujuannya, ucapkan terima kasih kepada pihak-pihak di atas dengan kalimat yang tulus dan spesifik, lalu tutup dengan harapan semoga skripsi ini bermanfaat. Jangan tambahkan nama atau pihak yang tidak saya sebutkan.

English:

> I am writing the preface for my thesis titled {judul}, supervised by {pembimbing}. The people I want to thank: {ucapan}. Please draft a polite, formal preface: open with gratitude, state the thesis title and its purpose, thank the people above with sincere and specific sentences, then close with a hope that this thesis will be useful. Do not add any names or parties I did not mention.

### 4. `latar-belakang` — Latar Belakang, Bab 1 (Grok)

Placeholders: topik, catatan, paragraf.

> Saya sedang menulis bagian latar belakang untuk skripsi bertopik {topik}. Berikut poin-poin dari saya dan dosen pembimbing: {catatan}. Tolong rangkai poin-poin itu menjadi latar belakang yang runtut dengan struktur piramida terbalik, dari isu umum ke konteks lokal, lalu ke masalah spesifik penelitian saya. Sertakan data atau referensi pendukung bila ada, gunakan bahasa akademik standar skripsi, dan buat dalam {paragraf} paragraf yang mengalir dan siap dipakai di dokumen skripsi.

English:

> I am writing the background section for a thesis on {topik}. Here are the points from me and my supervisor: {catatan}. Please weave these points into a coherent background with an inverted-pyramid structure, from the general issue to the local context, then to the specific problem of my research. Include supporting data or references where available, use standard academic thesis language, and make it {paragraf} paragraphs that flow and are ready to use in the thesis document.

### 5. `rumusan-masalah` — Rumusan Masalah & Tujuan, Bab 1 (ChatGPT)

Placeholders: topik, masalah, tujuan.

> Saya sedang menulis Bab 1 skripsi bertopik {topik}. Masalah yang saya hadapi: {masalah}. Tujuan penelitian saya: {tujuan}. Tolong bantu saya merumuskan masalah penelitian dalam bentuk pertanyaan penelitian yang jelas dan terukur, lalu turunkan tujuan penelitian yang sesuai dengan pertanyaan itu. Beri 2-3 rumusan masalah beserta tujuan masing-masing, dan jelaskan singkat kenapa rumusan itu layak diteliti.

English:

> I am writing Chapter 1 of my thesis on {topik}. The problem I am facing: {masalah}. My research objective: {tujuan}. Please help me turn this into clear, measurable research questions, then derive matching research objectives for each question. Give 2-3 problem statements with their objectives, and briefly explain why each is worth researching.

### 6. `banding-teori` — Membandingkan 3 Teori, Bab 2 (Grok)

Placeholders: judul.

> Saya sedang menulis skripsi tentang {judul}. Tolong carikan tiga teori yang relevan dengan topik ini, lalu bandingkan ketiganya dalam tabel: nama teori, tokoh atau penelitinya, konsep utama, kelebihan dan keterbatasan, serta relevansinya dengan penelitian saya. Di akhir, beri rekomendasi teori mana yang paling cocok dijadikan landasan teori penelitian saya.

English:

> I am writing a thesis about {judul}. Please find three theories relevant to this topic, then compare them in a table: theory name, its figure or researcher, main concepts, strengths and limitations, and relevance to my research. At the end, recommend which theory fits best as the theoretical foundation of my research.

### 7. `review-terdahulu` — Review Penelitian Terdahulu, Bab 2 (Grok)

Placeholders: judul, daftar, gaya.

> Saya sedang meneliti {judul}. Berikut daftar penelitian terdahulu yang saya jadikan rujukan: {daftar}. Tolong buat ulasan kritis terhadap penelitian-penelitian itu, dengan fokus pada metode, sampel, hasil, dan keterbatasannya. Jelaskan celah penelitian (research gap) yang belum banyak diteliti dan bagaimana penelitian saya bisa mengisinya. Tulis dalam bahasa akademik, sekitar 3-4 paragraf, dengan sitasi gaya {gaya}.

English:

> I am researching {judul}. Here is the list of prior studies I am using as references: {daftar}. Please write a critical review of these studies, focusing on method, sample, findings, and limitations. Explain the research gap that has not been widely studied and how my research can fill it. Write in academic language, about 3-4 paragraphs, with citations in {gaya} style.

### 8. `metodologi` — Metodologi Penelitian, Bab 3 (ChatGPT)

Placeholders: judul, jenis, metode, populasi, pengumpulan, analisis.

> Saya sedang menulis Bab 3 Metodologi Penelitian untuk skripsi berjudul {judul}. Jenis penelitian saya: {jenis}. Metode yang digunakan: {metode}. Populasi dan sampel: {populasi}. Teknik pengumpulan data: {pengumpulan}. Teknik analisis data: {analisis}. Susunlah Bab 3 yang lengkap dan logis, mencakup desain penelitian, definisi operasional variabel, populasi dan sampel, instrumen penelitian, teknik pengumpulan data, dan teknik analisis data. Pastikan isinya selaras dengan judul serta Bab 1 dan 2, dan jelaskan alasan metode ini paling tepat untuk penelitian saya, dengan bahasa akademik yang rapi.

English:

> I am writing Chapter 3, Research Methodology, for a thesis titled {judul}. My research type: {jenis}. Method used: {metode}. Population and sample: {populasi}. Data collection technique: {pengumpulan}. Data analysis technique: {analisis}. Draft a complete and logical Chapter 3, covering research design, operational definitions of variables, population and sample, research instruments, data collection techniques, and data analysis techniques. Make sure the content aligns with the title and Chapters 1 and 2, and explain why this method is the best fit for my research, in neat academic language.

### 9. `hubungan-variabel` — Hubungan Antar Variabel, Bab 3 (ChatGPT / Grok)

Placeholders: judul, variabel_x, variabel_y, variabel_z.

> Saya sedang menulis Bab 3 skripsi berjudul {judul}. Variabel penelitian saya: variabel X = {variabel_x}, variabel Y = {variabel_y}, variabel Z = {variabel_z} (bila ada). Tolong buat paragraf yang menjelaskan hubungan antar variabel ini berdasarkan teori yang relevan. Uraikan secara runtut, mulai dari hubungan X ke Y, lalu Z bila ada. Jelaskan mengapa hubungan ini penting untuk diteliti, dan dukung dengan minimal 3 referensi dari penelitian terdahulu (format APA 7th).

English:

> I am writing Chapter 3 of a thesis titled {judul}. My research variables: variable X = {variabel_x}, variable Y = {variabel_y}, variable Z = {variabel_z} (if any). Please write a paragraph explaining the relationships between these variables based on relevant theory. Lay it out in order, starting with the X-to-Y relationship, then Z if any. Explain why this relationship is important to study, and support it with at least 3 references from prior research (APA 7th format).

### 10. `hipotesis` — Perkiraan Hipotesis, Bab 3 (Grok)

Placeholders: judul, variabel.

> Saya sedang menyusun hipotesis untuk skripsi berjudul {judul}. Variabel yang saya teliti: {variabel}. Tolong carikan minimal 5 penelitian terdahulu yang meneliti hubungan serupa. Ringkas temuan utama masing-masing penelitian, lalu susun hipotesis yang logis dan bisa diuji. Format hasilnya: ringkasan penelitian terdahulu (penulis, tahun, temuan, relevansi), sintesis hubungan antar penelitian (pola, konsistensi, atau perdebatan yang ada), dan hipotesis saya (H0, H1, dst) dalam format yang jelas dan siap dimasukkan ke Bab 3.

English:

> I am drafting hypotheses for a thesis titled {judul}. The variables I am studying: {variabel}. Please find at least 5 prior studies that examined similar relationships. Summarize each study's main findings, then formulate logical, testable hypotheses. Format the result as: summary of prior research (author, year, findings, relevance), synthesis of the relationships between studies (patterns, consistencies, or debates), and my hypotheses (H0, H1, etc.) in a clear format ready for Chapter 3.

### 11. `mixed-methods` — Analisis Mixed-Methods, Bab 4 (ChatGPT)

Placeholders: judul, kuantitatif, kualitatif.

> Saya sedang menganalisis data penelitian mixed method untuk skripsi berjudul {judul}. Metode kuantitatif saya: {kuantitatif}. Metode kualitatif saya: {kualitatif}. Saya akan melampirkan file data mentah saya. Tolong analisis dengan langkah: (1) Analisis kuantitatif: bersihkan data dan jelaskan penanganan missing value, lakukan uji statistik yang sesuai, sajikan hasil dalam tabel beserta interpretasi (p-value, signifikansi, effect size), dan buat visualisasi sederhana bila relevan. (2) Analisis kualitatif: lakukan coding tematik, sajikan tema utama beserta kutipan perwakilan responden, dan interpretasikan maknanya. (3) Integrasi: gabungkan kedua hasil, tunjukkan apakah keduanya saling mendukung, melengkapi, atau bertentangan, dan buat kesimpulan sementara yang menjawab rumusan masalah. Gunakan bahasa akademik yang jelas dan sistematis, dengan format akhir yang siap dimasukkan ke Bab 4.

English:

> I am analyzing mixed-method research data for a thesis titled {judul}. My quantitative method: {kuantitatif}. My qualitative method: {kualitatif}. I will attach my raw data files. Please analyze with these steps: (1) Quantitative analysis: clean the data and explain how missing values are handled, run the appropriate statistical tests, present the results in tables with interpretation (p-value, significance, effect size), and make simple visualizations where relevant. (2) Qualitative analysis: do thematic coding, present the main themes with representative respondent quotes, and interpret their meaning. (3) Integration: combine both results, show whether they support, complement, or contradict each other, and draw a preliminary conclusion that answers the problem statement. Use clear, systematic academic language, with a final format ready for Chapter 4.

### 12. `saran` — Saran Penelitian, Bab 5 (ChatGPT)

Placeholders: judul, hasil.

> Saya sedang menyusun Bab 5 skripsi berjudul {judul}. Berdasarkan hasil penelitian saya berikut: {hasil}, tolong buatkan saran penelitian yang konstruktif untuk tiga pihak: (1) praktisi atau industri, (2) akademisi, dan (3) peneliti berikutnya. Tulis dengan bahasa akademik, masing-masing satu paragraf, dan pastikan setiap saran bisa diterapkan dan relevan dengan temuan penelitian saya.

English:

> I am drafting Chapter 5 of a thesis titled {judul}. Based on my findings below: {hasil}, please write constructive research suggestions for three audiences: (1) practitioners or industry, (2) academics, and (3) future researchers. Write in academic language, one paragraph each, and make sure every suggestion is actionable and relevant to my findings.

### 13. `keterbatasan` — Keterbatasan + Peluang Penelitian, Bab 5 (ChatGPT)

Placeholders: judul, metode, data.

> Saya sedang menulis Bab 5 skripsi berjudul {judul}. Metode penelitian saya: {metode}, dengan data: {data}. Tolong buatkan bagian keterbatasan penelitian yang ditulis secara elegan dan profesional, tanpa melemahkan hasil penelitian, lalu lanjutkan dengan peluang penelitian lanjutan. Berikan 3-5 ide penelitian berikutnya yang relevan, misalnya metode baru, populasi berbeda, atau variabel tambahan, dan jelaskan mengapa setiap ide penting untuk dikaji.

English:

> I am writing Chapter 5 of a thesis titled {judul}. My research method: {metode}, with data: {data}. Please write a limitations section that is elegant and professional, without weakening the findings, then continue with opportunities for future research. Give 3-5 ideas for follow-up studies, such as a new method, a different population, or additional variables, and explain why each idea matters to study.

### 14. `review-draf` — Review Draf Skripsi, Persiapan Sidang (Claude / Manus)

Placeholders: none (the student attaches their thesis file).

> Saya akan melampirkan file skripsi saya (PDF/DOC). Tolong baca dan analisis seluruh isinya, dan berperan sebagai dosen pembimbing sekaligus dosen penguji yang objektif dan kritis. Beri masukan tentang bagian yang masih lemah, berpotensi jadi revisi, atau bisa memicu pertanyaan saat seminar dan sidang. Jelaskan secara spesifik letak masalahnya (bab atau subbab), alasan bagian itu dinilai kurang kuat, dan aspek apa yang sebaiknya diperdalam, tanpa langsung menuliskan revisinya. Sebutkan juga kekuatan skripsi saya, dari argumentasi, teori, metodologi, analisis, sampai kebaruan penelitian. Terakhir, evaluasi aspek teknis penulisan: sistematika, alur antarparagraf, konsistensi istilah, kualitas sitasi dan daftar pustaka, format tabel atau gambar, serta potensi kesalahan akademik lainnya. Sajikan evaluasi dalam kategori yang jelas, diurutkan berdasarkan prioritas (tinggi, sedang, rendah), agar saya tahu bagian mana yang harus diperbaiki dulu.

English:

> I will attach my thesis file (PDF/DOC). Please read and analyze all of it, and act as an objective, critical supervisor and examiner. Give feedback on the parts that are still weak, could trigger revisions, or could prompt questions during the seminar and defense. Explain specifically where the problem is (chapter or subchapter), why that part is considered weak, and what should be deepened, without writing the revision itself. Also mention my thesis's strengths, from argumentation, theory, methodology, analysis, to research novelty. Finally, evaluate the technical writing: structure, flow between paragraphs, term consistency, citation and bibliography quality, table or figure formatting, and other potential academic errors. Present the evaluation in clear categories, ordered by priority (high, medium, low), so I know which part to fix first.

### 15. `ppt` — Skripsi Menjadi PowerPoint (Sidang, ChatGPT)

Placeholders: judul, jumlah_slide.

> Saya ingin mengubah skripsi saya berjudul {judul} menjadi slide presentasi PowerPoint. Saya akan melampirkan file skripsinya. Tolong rangkum setiap bab menjadi slide dengan judul yang singkat dan menarik. Isi tiap slide berupa poin-poin penting (maksimal 5 poin per slide), ditambah 1-2 kalimat penjelas untuk setiap slide agar saya tahu apa yang harus diucapkan. Ikuti struktur presentasi skripsi: latar belakang, rumusan masalah, tujuan, tinjauan pustaka, metode, hasil, pembahasan, kesimpulan, dan saran. Bila perlu, rekomendasikan grafik, tabel, atau diagram untuk memperjelas. Hasil akhirnya adalah presentasi sebanyak {jumlah_slide} slide yang siap dipakai tanpa banyak edit.

English:

> I want to turn my thesis titled {judul} into a PowerPoint presentation. I will attach the thesis file. Please summarize each chapter into slides with short, engaging titles. Each slide's content should be key points (at most 5 points per slide), plus 1-2 explanatory sentences per slide so I know what to say. Follow the thesis presentation structure: background, problem statement, objectives, literature review, method, results, discussion, conclusions, and suggestions. Where needed, recommend charts, tables, or diagrams for clarity. The final result is a presentation of {jumlah_slide} slides ready to use with little editing.

### 16. `cue-card` — Cue Card Presentasi (Sidang, ChatGPT)

Placeholders: none (follows the PPT from prompt 15).

> Tolong buatkan cue card singkat dan padat untuk membantu saya saat presentasi skripsi. Bagi per slide sesuai urutan PPT skripsi saya. Tulis poin-poin atau kalimat kunci yang harus saya ucapkan, dengan bahasa lisan yang natural tapi tetap profesional. Jangan terlalu panjang, cukup 2-3 kalimat per slide supaya mudah dihafalkan. Tambahkan tips intonasi atau gestur (misalnya: senyum di awal, lihat audiens saat menyebut hasil utama). Pastikan cue card ini membuat saya percaya diri, tidak terdengar kaku, dan membantu menjawab kemungkinan pertanyaan dari penguji.

English:

> Please make short, compact cue cards to help me during my thesis presentation. Split them per slide following my thesis PPT order. Write the key points or sentences I must say, in natural spoken language that stays professional. Keep it short, just 2-3 sentences per slide so it is easy to memorize. Add tips on intonation or gestures (for example: smile at the start, look at the audience when stating the main result). Make sure these cue cards make me confident, not stiff, and help me answer possible questions from the examiners.

### 17. `blog` — Skripsi Menjadi Artikel Blog (Publikasi, ChatGPT)

Placeholders: judul, platform, kata.

> Saya ingin mengubah skripsi saya berjudul {judul} menjadi artikel pendek yang siap dipublikasikan di {platform}. Saya akan melampirkan file skripsinya. Tolong ambil intisarinya lalu tulis ulang dengan bahasa yang santai, mudah dipahami pembaca awam, dan tetap menarik. Panjang artikel sekitar {kata} kata. Susun dengan struktur yang runtut: mulai dari pembuka yang menarik perhatian (fakta menarik, pertanyaan, atau fenomena terkini), lalu paparkan masalah yang saya teliti dan relevansinya, jelaskan metode dan temuan utama secara singkat tanpa terlalu banyak jargon, dan tutup dengan manfaat praktis penelitian ini bagi pembaca. Bila perlu, tambahkan statistik, contoh kasus, atau call-to-action, dan pastikan artikel mencantumkan kredit ke penelitian saya agar bisa dipakai sebagai portofolio.

English:

> I want to turn my thesis titled {judul} into a short article ready to publish on {platform}. I will attach the thesis file. Please take its essence and rewrite it in relaxed language that is easy for lay readers to understand, and still engaging. The article should be about {kata} words long. Structure it in order: start with an attention-grabbing opening (an interesting fact, a question, or a current phenomenon), then present the problem I studied and its relevance, briefly explain the method and main findings without too much jargon, and close with the practical benefit of this research for readers. Where needed, add statistics, case examples, or a call-to-action, and make sure the article credits my research so it can serve as a portfolio.

### 18. `jurnal` — Skripsi Menjadi Artikel Jurnal (Publikasi, ChatGPT)

Placeholders: bagian, jumlah.

> Saya ingin memublikasikan jurnal berdasarkan skripsi saya. Ini bagian yang perlu dirangkum menjadi paragraf yang lebih singkat untuk jurnal saya: {bagian}. Buatkan maksimal sebanyak {jumlah} paragraf atau kata. Pertahankan sitasinya dan jangan membuang inti tiap paragraf. Gunakan bahasa yang humanis dan tidak terkesan robotik. Hindari kata yang berulang dan struktur kalimat yang generik, variasikan panjang kalimat, dan hindari em-dash dan titik koma. Berikut paragraf yang perlu dipersingkat: [tempel paragraf kamu di sini, satu bagian saja].

English:

> I want to publish a journal article based on my thesis. This is the section that needs to be condensed into shorter paragraphs for my journal: {bagian}. Make at most {jumlah} paragraphs or words. Keep the citations and do not drop the core of each paragraph. Use human, non-robotic language. Avoid repeated words and generic sentence structures, vary sentence length, and avoid em-dashes and semicolons. Here is the paragraph to shorten: [paste your paragraph here, one section only].
## After drafting: Humanize and check the draft

A filled prompt produces a draft, not a finished chapter. Two more tools in the same file finish the job (see `academic-quality-check`):

**Humanize — style rewrite suggestions.** Stiff Indonesian prose gets concrete before/after suggestions: light verbs become direct verbs ("melakukan pengukuran terhadap" → "mengukur"), connectors are dropped, "yang mana" splits the sentence. Passive voice, `dimana`, and flat rhythm get guidance instead of a made-up rewrite. Nothing changes unless `--apply` is given, and then only the mechanical suggestions — the original is never touched (output goes to `<file>.humanized.txt` unless `--out` or `--in-place` with a `.bak` backup is passed).

```bash
python3 academic_tools.py humanize draf-bab1.txt
python3 academic_tools.py humanize draf-bab1.txt --apply
```

**Quality check — one pass before submission.** `analyze` scores the draft 0–100 across jargon, citations, DOI verification, and style, and lists what to fix. Add `--suggest` for the Humanize suggestions in the same pass.

```bash
python3 academic_tools.py analyze draf-bab1.txt --refs my-refs.json --suggest
```

In the interactive menu, Humanize is option 5 and Analisis Kualitas is option 4.

## Usage

```bash
python3 academic_tools.py prompts --list
python3 academic_tools.py prompts latar-belakang
python3 academic_tools.py prompts roadmap --set judul="..." --set teori="..." --set metode="..." --set bulan=6 --set tanggal="11 November 2026"
# English version of any template:
python3 academic_tools.py prompts abstrak --lang en --set judul="..." --set masalah="..." --set metode="..." --set hasil="..." --set kunci="..."
```

Or open the interactive menu (`python3 academic_tools.py`) and pick option 3, Prompt Skripsi.
