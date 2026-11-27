# Git/GitHub từ đầu

Git giữ lịch sử thay đổi trên máy; GitHub lưu repository và PR. Dùng tài khoản
của chính bạn, xác minh email hoặc dùng GitHub noreply đúng account.
Git name/email là attribution; quyền push cần được cấp riêng.

1. Cài Git từ https://git-scm.com/downloads, kiểm `git --version`.
2. Đợi TV5 publish base, clone repo. Trong clone đặt `git config user.name "TEN_CUA_BAN"`
   và `git config user.email "EMAIL_VERIFIED_HOAC_NOREPLY"`.
3. Kiểm bằng `git config --get user.name` và `git config --get user.email`.
4. Tạo branch riêng từ common base, chỉnh files mình sở hữu và chạy tests.
5. Kiểm `git status`, `git diff`, `.gitignore`, `git log -5` trước stage/commit.
6. Stage files cụ thể, kiểm `git diff --cached`, commit nêu rõ thay đổi/lý do.
7. Push branch của mình, mở PR để review. Merge vào main sau review và checks.

Ví dụ đóng góp: sửa Kaggle path ambiguity kèm regression test, thêm missing-shard
check, hoặc GPU report/troubleshooting có evidence. Mỗi commit giải quyết công việc
thật. Giữ author đúng người thực hiện và lịch sử commit cũ.

Repo hiện public; images, private bundles, secrets, weights, raw main outputs,
venv và notebook outputs nhạy cảm giữ ngoài Git. Xem CONTRIBUTION_CHECKLIST.md.
Nguồn: [GitHub commit email](https://docs.github.com/en/account-and-profile/how-tos/email-preferences/setting-your-commit-email-address).
