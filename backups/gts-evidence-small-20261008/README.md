# GTS 小文件实验记录备份（2026-10-08）

备份保存此前仅位于被 Git 忽略的 local 目录中的部分实验记录，方便离开服务器临时目录后仍能核对实验过程。源文件和生产分支均保留。

本次只选择 CSV、JSON、日志、Markdown、运行源码和查询编号等小文件；不包含完整原始数据、二进制结果、Nsight 文件、编译产物、TXT 数据集或静态汇编转储，也不包含 gts_batch_evidence_20261001。此包不能替代原始目录的完整备份。

MANIFEST.json 列出归档范围、所有入选文件的原始相对路径、大小及 SHA-256，以及按扩展名统计的未入选文件。归档已逐文件读取并核对清单。

校验下载文件：

    sha256sum -c SHA256SUMS

恢复到新目录；归档内路径相对于原用户工作区根目录：

    mkdir restored-records
    tar -xzf raw-text-evidence-20261008.tar.gz -C restored-records

原始目录不应仅凭这个小文件备份整目录删除。完整原始数据和参考输出仍需另行持久化。
