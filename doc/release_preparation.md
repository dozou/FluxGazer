# FluxGazer ソース公開準備

確認日：2026-09-06。対象は自作ソースのMIT公開準備であり、GitHub公開、リモートへのpush、PyPI登録、実行ファイル配布は実施しない。

## 準備内容

- パッケージを `flux_gazer` に変更。`main.py`、`python -m flux_gazer`、`run.ps1` による起動を用意。
- `LICENSE` にMIT本文と「Copyright (c) 2026 FluxGazer contributors」を記載。
- READMEにAIベースの開発目的、現状の精度・実用性の位置づけ、ライセンス範囲を記載。
- `THIRD_PARTY_NOTICES.md` に直接依存とTriangle・Qtの留意点を記載。
- `.gitignore` に環境・成果物・IDE設定・環境変数ファイル等を指定。ソースアーカイブ向けの `.gitattributes` も追加。
- モデルJSONの `motor_sim.standard_spm` は既存のデータ形式として維持。Pythonパッケージ名とは独立。

## 公開前に扱う事項

ライブラリを含む実行ファイルの商用配布は今回の準備対象外。Triangle本体の条件はMITと異なるため、許諾確認またはメッシャーの置換が必要。Qtおよび推移的なバイナリ依存も実際の配布物に対して確認する。

Git履歴には既存のIDE設定が含まれている可能性がある。ignoreは過去の履歴からファイルを消す機能ではない。公開リポジトリの履歴全体を含む機密情報監査や権利監査は今回完了したとは扱わない。リモート公開先や公開版番号は未設定。

## 検証コマンド

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe main.py
# パッケージとして起動する場合
.\.venv\Scripts\python.exe -m flux_gazer
```

ソース公開時は `flux_gazer/`、`tests/`、`doc/`、必要な `examples/`、起動・検証スクリプト、README、requirements、LICENSE、THIRD_PARTY_NOTICESを含める。`.venv*`、`.idea`、`artifacts`、キャッシュ・個人環境設定は含めない。
