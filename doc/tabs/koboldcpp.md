# KoboldCppタブ

## 目的
使用モデルの選択と、KoboldCppサーバーの起動/停止を行います。

## 画面項目
- `モデル選択`
- `layers`
- `context_length`
- `起動` / `終了`
- `koboldcpp 実行ファイルパス（起動する場合のみ）`
- `base_url`

## モデル一覧の生成
`backend.py` 初期化時に以下をマージして候補を作ります。
- `models/llm.json` の定義モデル
- `models/*.gguf` のローカルモデル（未定義分は `オリジナル/...` として追加）

## 起動フロー
`起動` ボタンで以下を実行します。

1. モデル未配置なら `models/` に自動ダウンロード
2. `backend.start()` で KoboldCpp を subprocess 起動
3. `base_url` のポートに対して待機確認
4. 接続確認できたら `起動完了`

起動コマンド例:

```text
koboldcpp --model models/<model>.gguf --port 5001 --gpulayers <layers> --contextsize <context_length>
```

## 外部起動サーバーを使う場合
- KoboldCppを手動起動済みなら、`base_url` を合わせるだけで利用できます
- `koboldcpp 実行ファイルパス` は未使用でも可

## 停止フロー
`終了` ボタンで `backend.stop()` が呼ばれ、対象プロセスに停止シグナルを送ります。

## 注意点
- `layers` / `context_length` を上げるとVRAM・RAM要求が増加
- `base_url` のポート指定が不正な場合、接続待機に失敗します
