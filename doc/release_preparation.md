# FluxGazer ソース公開準備

更新日：2026-09-06。FluxGazerを開発版（Experimental）としてソース公開するための準備記録。実用精度を保証した正式版、PyPIパッケージ、依存ライブラリ同梱の実行ファイルのリリースではない。

## リポジトリと公開予定

- 接続先：[dozou/FluxGazer](https://github.com/dozou/FluxGazer)、ブランチ：`master`。
- パッケージ移行とMIT公開準備のコミット `8c80c5b` はリモートへプッシュ済み。
- 今回はIDE設定の追跡解除と文書整理をコミットし、次のプッシュに備える。今回の作業ではプッシュやGitHubの公開範囲変更は行わない。
- GitHubのPublic/Private設定はプッシュとは別の設定。公開時にリポジトリ側で確認する。
- リリースタグ・版番号は未設定。

## 準備内容

- パッケージを `flux_gazer` に変更。`main.py`、`python -m flux_gazer`、`run.ps1` による起動を用意。
- `LICENSE` にMIT本文と「Copyright (c) 2026 FluxGazer contributors」を記載。
- READMEにAIベースの開発目的、現状の精度・実用性の位置づけ、ライセンス範囲を記載。
- `THIRD_PARTY_NOTICES.md` に直接依存とTriangle・Qtの留意点を記載。
- `.gitignore` に環境・成果物・IDE設定・環境変数ファイル等を指定。ソースアーカイブ向けの `.gitattributes` も追加。
- PyCharmの `.idea/` はGitの追跡から外す。ローカルの設定ファイルは残し、以後は `.gitignore` で除外する。
- モデルJSONの `motor_sim.standard_spm` は既存のデータ形式として維持。Pythonパッケージ名とは独立。

## 公開前に扱う事項

ライブラリを含む実行ファイルの商用配布は今回の準備対象外。Triangle本体の条件はMITと異なるため、許諾確認またはメッシャーの置換が必要。Qtおよび推移的なバイナリ依存も実際の配布物に対して確認する。

既存のGit履歴にはIDE設定が含まれている。今回の追跡解除は最新ツリーからの削除であり、過去コミットは書き換えない。公開リポジトリの履歴全体を含む機密情報監査や権利監査は完了したとは扱わない。

直近の既存環境での自動検証は39ケース通過。新規PCでcloneから依存導入・起動までの確認は未実施であり、既存環境の検証と区別する。

## 検証コマンド

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe main.py
# パッケージとして起動する場合
.\.venv\Scripts\python.exe -m flux_gazer
```

ソース公開時は `flux_gazer/`、`tests/`、`doc/`、必要な `examples/`、起動・検証スクリプト、README、requirements、LICENSE、THIRD_PARTY_NOTICESを含める。`.venv*`、`.idea`、`artifacts`、キャッシュ・個人環境設定は含めない。
