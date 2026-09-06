# Third-party dependencies

FluxGazer独自のソースコード・文書は [MIT License](LICENSE) で公開します。第三者のライブラリ、フォント、同梱バイナリには各権利者の条件が適用されます。本書は主要な直接依存の案内であり、上流のライセンス本文を置き換えるものではありません。確認日：2026-09-06。

|依存|ライセンス概要・参照|
|---|---|
|NumPy|BSD系。配布物には追加の第三者ライセンスあり。[上流](https://github.com/numpy/numpy/blob/main/LICENSE.txt)|
|SciPy|BSD系。BLAS等、配布物ごとの第三者条件にも従う。[上流](https://github.com/scipy/scipy/blob/main/LICENSE.txt)|
|Matplotlib|Matplotlib独自のBSD互換ライセンス、PSF由来の条件等。[上流](https://matplotlib.org/stable/project/license.html)|
|Shapely|BSD-3-Clause。GEOS等の同梱物は別条件。[上流](https://github.com/shapely/shapely/blob/main/LICENSE.txt)|
|PySide6 / Qt|LGPL/GPLまたは商用ライセンス。モジュール・配布形態により条件が異なる。[公式](https://doc.qt.io/qtforpython-6/commercial/index.html)|
|triangle Python wrapper|インストール済み20250106のメタデータとLICENSEはLGPL-3.0。内部Triangle本体の条件は下記を参照。[上流](https://github.com/drufat/triangle)|
|pytest|MIT。開発・検証用途。[上流](https://github.com/pytest-dev/pytest/blob/main/LICENSE)|

## Triangle本体の注意

Triangle本体はJonathan Richard Shewchuk氏の著作物です。公式サイトは、販売または商用製品への組込みにはライセンスが必要と案内しています。PythonラッパーのLGPL表示だけから、本体も同じ条件であるとは判断しないでください。[Triangle公式](https://www.cs.cmu.edu/~quake/triangle.html)、[本体ソース](https://github.com/drufat/triangle-c)

したがって、**FluxGazerの独自コードがMITであることは、現在の依存構成全体を制限なく商用再配布できることを意味しません。** 商用組込み・実行ファイル配布へ進む場合は、本体の許諾取得または適切なライセンスのメッシャーへの置換を検討してください。現在の公開準備は自作ソースの公開を対象とし、第三者ライブラリを同梱した配布物は作成していません。

## Qt・バイナリ・フォント

Qt/PySide6を同梱する場合は実際に含むモジュールとライセンスを確認し、必要な著作権表示・ライセンス本文・ソース提供等の義務に対応してください。[Qtのライセンス案内](https://doc.qt.io/qt-6/licensing.html)、[LGPLの義務](https://www.qt.io/development/open-source-lgpl-obligations)

WindowsのメイリオはOS上のファイルを参照するだけで、本リポジトリに含めません。仮想環境、インストール済みwheel、フォント、ネイティブDLLは公開対象に含めません。将来同梱する場合は推移的依存も含め、配布物単位でライセンス本文とNOTICEを収集してください。
