# Branch, PR và fork

TV5publishcommonbase trước, thôngbáobasebranch/commit. MỗiTVgitfetch/checkoutbase
rồi `git switch -c work/...` theoassignment. Không cùngsửa core runner.

Trướcpush: `git status --short`, `git diff --check`, `git diff --cached`,
`git log -5`, `python -m pytest -q`, `python scripts/check_repository.py`.
Khôngforcepush/sharedbranch hoặcreset côngviệc người khác. PR mô tảproblem,
behaviorchange,tests,cloudchecks thật/chưa chạy,scope/fingerprint impact.

Không có quyềnpush: forkGitHubvềaccountcủabạn,clonefork, `git remote add upstream https://github.com/MinhGioChai/cv-final-project.git`, fetchupstream, tạo featurebranch
từbase, pushoriginfork. TrênGitHubtạoPR:baseMinhGioChai/cv-final-project,
compareYOUR_LOGIN/branch. Khôngcầntokenngườikhác; logintrìnhduyệt/Gitcredentialmanager.

TV5review thật,testsCI đạt,mergeconflictsresolved mớimerge. Reviewnotebookdiff
khôngoutputs, ownership khôngchồngchéo, raw/metadata fingerprintcontract khôngnới.
Khôngsquash/rebase/commit bằngtênkhác đểgiảcredit; người đónggópđượcgiữattribution
đúngGit/GitHub, nếu squashthìTV5kiểmauthor/coauthor hợp lệ,cóđónggópthật.

Sau4PRmerge, checkoutcommoncommit vàfreezev2bằngapproverthật; tag/releasecùngSHA.
Chưa córelease này. Không dùng branchheadđangthayđổi làmPhaseBpin.
Nguồn: https://docs.github.com/en/pull-requests/how-tos/create-pull-requests/creating-a-pull-request
