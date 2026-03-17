# Easy Novel Assistant osuChitsu ドキュメント

このフォルダは、画面の各タブごとに使い方と内部仕様を分離して説明します。  
特に `context長圧縮方式` と `ガタライズスクリプト` は、実装に沿った技術説明を含めています。

## クイックスタート
1. `launch.bat` を実行
2. `KoboldCpp` タブでモデル選択して `起動`
3. `構成` と `パラメータ` を入力
4. 左側の `リトライ` で本文生成
5. `保存/終了` タブから保存

## タブ別ドキュメント
- `構成` タブ: `doc/tabs/composition.md`
- `パラメータ` タブ: `doc/tabs/parameters.md`
- `KoboldCpp` タブ: `doc/tabs/koboldcpp.md`
- `保存/終了` タブ: `doc/tabs/save-exit.md`
- `ガタライズスクリプト作成` タブ: `doc/tabs/gscript-editor.md`

## 関連ファイル
- モデル定義: `models/llm.json`
- ガタライズ既定辞書: `gscript.json`（暗号化JSON）
- UI本体: `main.py`
- 生成/圧縮バックエンド: `backend.py`
- ガタライズ編集ロジック: `gscript_edit.py`
- 簡易暗号処理: `cipher.py`
