# Phân công development và experimental execution

TV1–TV4 là role, chưa gán tên/GitHub cá nhân. TV5 là integration owner.

| Role | Shard dự kiến | Platform | Branch | PR |
|---|---|---|---|---|
| TV1 | qwen EN | colab | `work/main-qwen-en` | Add language-specific inference sharding and validation |
| TV2 | qwen VI | kaggle | `work/main-qwen-vi` | Add Kaggle main inference workflow and data validation |
| TV3 | gemma EN | colab | `work/main-gemma-en` | Add Colab main inference setup and Gemma GPU checks |
| TV4 | gemma VI | kaggle | `work/main-gemma-vi` | Add inference checkpoint recovery and shard result validation |

Mỗi shard có 1.000 cells, cả bốn có 4.000 cells. Các shard dùng cùng dataset,
protocol và implementation đã được chốt. TV4 chỉ dùng Kaggle khi native BF16
được kiểm chứng; nếu không, dùng môi trường BF16 được TV5 xác nhận và ghi
platform/GPU thật. Không tự đổi sang FP16.

TV5: publish common base, review PR, giải quyết conflict, kiểm CPU tests/source integrity,
chốt common commit/release, protocol v2 và bundle cuối. Mỗi TV1–TV4 tự commit phần mình.
Contributions code/docs/tests khác với experimental GPU evidence; ghi đúng người thực hiện.
Nếu component đã đủ tốt, người owner đóng góp kiểm chứng thật/tests/troubleshooting,
không viết code thừa để có commit. Không chia một thay đổi thành commit hình thức.
