# Git Baseline Provenance Follow-up

## Repository facts

- Current branch: `main`.
- HEAD: `510f6415b6af535ceec77213f0b0c7d5082123f7`.
- Local `main`, `master`, `phase1-baseline`, remote-tracking `origin/master` và live remote `refs/heads/master` đều trỏ `510f641…`.
- Live `git ls-remote --symref origin HEAD refs/heads/master refs/heads/main` xác nhận remote HEAD là `refs/heads/master`; remote không trả `refs/heads/main`.
- Chỉ có remote `origin = https://github.com/BuiHuy16/ByteMe-phase2.git`; không có `upstream` remote.
- Reflog local ghi `phase1-baseline` và `main` được tạo từ `origin/master` ngày 2026-11-17. Branch là mutable ref, không phải immutable provenance marker.
- Public GitHub REST metadata không lấy được do unauthenticated API rate limit; không dùng kết quả rỗng đó làm bằng chứng fork/upstream.

## Commit chain and change classification

| Commit | Parent | Author/commit time (UTC+07) | Verified content |
|---|---|---|---|
| `cfe22229d99dc7a26020ec3a59953e1eb57b4bab` | `fa21cf0…` | 2026-10-29 08:03:43 | Pre-refactor tree trong chain hiện có; commit này sửa README security assessment. |
| `1ee1cbf7b8d6d37f71c8a30ef57e0d68a3497763` | `cfe2222…` | 2026-11-06 23:36:41 | **Commit chuyển source/test từ package-by-feature sang package-by-layer**: 67 files, 173 insertions/186 deletions; phần lớn là rename/package/import/test-rule update. Không đổi `pom.xml`, resources, Docker/Compose, schema/SQL/YAML/properties. |
| `5a7bf4004abad672b92b7be1e3d83e8d19e81470` | `1ee1cbf…` | 2026-11-06 | Chỉ sửa `docs/architecture-single-restaurant.md`. |
| `510f6415b6af535ceec77213f0b0c7d5082123f7` | `5a7bf40…` | 2026-11-06 23:38:44 | Chỉ sửa `README.md`. |

Do hai commit sau `1ee1cbf…` chỉ đổi tài liệu, executable source/test/config ở HEAD mang cùng architectural refactor với `1ee1cbf…`.

Commit metadata và message chỉ xác định ai/timestamp/subject đã ghi trong object Git; chúng **không** tự chứng minh ownership theo giai đoạn hoặc intent Phase 2. Các tài liệu Phase 0–1 hiện có coi tree `510f641…` là As-Is Phase 1 candidate và được lập/review ngày 2026-11-17, sau commit ngày 2026-11-06. Đây là bằng chứng nội bộ nhất quán rằng refactor đã có trước assessment Phase 2 được ghi nhận trong clone, nhưng `docs/phase2/` hiện untracked và không phải nguồn độc lập/bất biến để chứng minh thời điểm nhóm thực sự bắt đầu Phase 2.

## Findings

1. Commit đổi kiến trúc là `1ee1cbf…`.
2. Có bằng chứng Git rằng commit này tồn tại trước mốc local `main`/`phase1-baseline` creation và trước các tài liệu assessment ngày 2026-11-17; **không đủ bằng chứng độc lập để kết luận nó tồn tại trước thời điểm thực tế nhóm bắt đầu Phase 2**.
3. Fork clone có origin và commit metadata, nhưng không có upstream remote/ref, tag pre-Phase-2, merge/PR marker hoặc immutable decision record chỉ ra repository nguồn.
4. Không tìm thấy bằng chứng độc lập xác định `1ee1cbf…` là treatment Phase 2; đồng thời cũng không có bằng chứng độc lập đủ mạnh xác định nó thuộc Phase 1.
5. Classification Phase 1/Phase 2 của `1ee1cbf…`: **PENDING**.

## Baseline candidates and before/after consequence

| Candidate | Provenance strength | Consequence |
|---|---|---|
| `510f641…` (runtime tree tương đương `1ee1cbf…`, chỉ có thêm docs) | **Tốt nhất trong evidence hiện có**: HEAD, live remote master, local `phase1-baseline`, Phase 0–1 docs và official 90/90 runtime evidence đều hội tụ | Dùng được làm current executable candidate, nhưng nếu `1ee1cbf…` là treatment Phase 2 thì “before” đã chứa treatment và before/after bị contaminated. |
| `cfe2222…` | Rõ ràng đứng ngay trước architectural refactor trong commit chain | Là pre-refactor candidate theo Git, nhưng chưa được runtime-verified trong G2.1 này và chưa được chứng minh là official Phase 1 endpoint; chọn nó cần team decision và một verification riêng. |

Kết luận: **không đổi baseline SHA**. `510f641…` có provenance tương đối tốt nhất nhưng chưa đủ điều kiện được tuyên bố chắc chắn là pre-improvement baseline. Cần một nguồn độc lập (upstream ref/history, PR/issue, signed decision/minutes hoặc artifact Phase 1 gắn SHA) để đóng classification.

