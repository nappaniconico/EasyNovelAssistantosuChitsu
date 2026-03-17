# パラメータタブ

## 画面項目
- `temperature`: 高いほどランダム性が増加
- `top_k`: 候補語彙の上位K制限
- `top_p`: 累積確率Pで語彙候補を制限
- `repeat_penalty`: 同語句の反復抑制
- `max_new_tokens`: 1回の追加生成量
- `context長圧縮方式`: `シンプル` / `AI圧縮`

## KoboldCppへ送る生成パラメータ
内部では `backend.py` の `generate_polled_stream()` で次のpayloadを送信します。

- `temperature`
- `top_k`
- `top_p`
- `rep_pen`（UIの `repeat_penalty`）
- `max_length`（UIの `max_new_tokens`）

## context長圧縮方式の技術仕様
圧縮処理は `backend.py` の `comp_hub()` で実行されます。  
処理順は次の通りです。

1. テンプレート適用済みプロンプトを作成
2. `/api/extra/tokencount` と `/api/extra/true_max_context_length` で超過量を計測
3. `max_new_tokens` を加味して超過判定
4. 超過時に圧縮方式ごとの処理へ分岐

判定式（概念）は以下です。

```text
check_over_tokens(formatted_prompt) + max_new_tokens < 0 なら圧縮不要
```

### シンプル
行単位で本文の先頭を削り、トークン上限に収まるまで繰り返します。

- 実装: `simple_compresser()`
- 入力本文を `\n` で分割
- 超過量と現在トークン数から、削除開始位置の初期値を推定
- 収まるまで先頭を1行ずつ追加削除

特徴:
- 速い
- 先頭文脈が落ちやすい（長編で伏線参照が弱まる）

### AI圧縮
補助モデルで本文を要約しながら圧縮します。

- 実装: `ai_compresser()`
- 補助モデル: `models/LFM2.5-1.2B-JP-Q8_0.gguf`
- 補助KoboldCppポート: `5015`
- 要約プロンプト: `以下の文章を3文以内で要約してください。`
- 本文を20行チャンクに分割し、先頭チャンクから順次要約に置換
- 上限に収まるまで要約チャンク数を増やす

特徴:
- 文脈保持は `シンプル` より有利
- 補助モデル起動分だけ遅い

## テンプレート適用
モデル名に応じて `chat_template.py` のテンプレートを選択します。
- `oss_V / oss_M / oss_L` -> `mistral`
- `oss_Q` -> `qwen3-instruct`
- その他は `chatml` が既定

## 注意点
- context上限超過時はUIに警告が出ます
- `AI圧縮` は補助KoboldCpp起動が必要なため、環境によっては失敗する場合があります
