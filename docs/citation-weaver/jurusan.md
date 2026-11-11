# Jurusan & Gaya Sitasi yang Direkomendasikan / Majors & Recommended Citation Styles

Setiap jurusan punya gaya sitasi yang umum dipakai. Ini rekomendasi —
`--style` selalu bisa meng-override. / Each major has a commonly used
citation style. This is a recommendation — `--style` always overrides it.

| Jurusan (ID) | Major (EN) | Gaya / Style |
|---|---|---|
| Kedokteran | Medicine | Vancouver |
| Keperawatan | Nursing | APA |
| Farmasi | Pharmacy | Vancouver |
| Kesehatan Masyarakat | Public Health | APA |
| Psikologi | Psychology | APA |
| Hukum | Law | Chicago |
| Ekonomi | Economics | Harvard |
| Manajemen | Management | APA |
| Akuntansi | Accounting | APA |
| Teknik Informatika | Informatics | IEEE |
| Ilmu Komputer | Computer Science | IEEE |
| Teknik Elektro | Electrical Engineering | IEEE |
| Teknik Sipil | Civil Engineering | IEEE |
| Teknik Mesin | Mechanical Engineering | IEEE |
| Pendidikan | Education | APA |
| Sastra Inggris | English Literature | MLA |
| Bahasa Indonesia | Indonesian Language | MLA |
| Sejarah | History | Chicago |
| Sosiologi | Sociology | APA |
| Biologi | Biology | APA |
| Fisika | Physics | IEEE |

Lihat daftar lengkap lewat CLI / See the full list via CLI:

```bash
python3 citation_weaver.py --list-jurusan
python3 citation_weaver.py --text "..." --refs demos/citation-weaver/references.json --jurusan Kedokteran
```
