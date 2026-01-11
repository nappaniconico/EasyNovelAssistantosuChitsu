# Easy Novel Assistant osuChitsu  

KoboldCpp を使って小説生成を行う Gradio アプリです。プロンプト補助、パラメータ調整、出力保存、ガタライズスクリプト編集を備えています。

## 動作環境
- Windows 10/11
- Python 3.11 以上
- NVIDIA GeForce RTX 20 / 30 / 40 番台で動作確認済み
- KoboldCpp（同梱の `koboldcpp.exe` か外部起動のどちらでも可）

## インストール  
### ワンステップインストール (おすすめ)  
[onestep-install.bat](https://raw.githubusercontent.com/nappaniconico/EasyNovelAssistantosuChitsu/refs/heads/main/onestep-install.bat)を実行  
Python環境の構築やkoboldcpp.exeのダウンロードを自動的に行います。

### マニュアルインストール 
自身でのPythonまたはuvのインストール、gitのインストールが可能な場合は以下のいずれかの手順でもインストール可能です。  

#### venv を使う場合  
1. Pythonがインストール済みであることを確認する
2. アプリを配置したいフォルダでコマンドプロンプトを起動し、`git clone https://github.com/nappaniconico/EasyNovelAssistantosuChitsu.git`を実行する
3. そのまま同じコマンドプロンプトで`cd EasyNovelAssistantosuChitsu/setup && create_venv.bat`を実行する
4. そのまま同じコマンドプロンプトで`cd setup && download_koboldcpp.bat`を実行する

#### uv を使う場合 (おすすめ)  
1. Pythonがインストール済みであることを確認する
2. アプリを配置したいフォルダでコマンドプロンプトを起動し、`git clone https://github.com/nappaniconico/EasyNovelAssistantosuChitsu.git`を実行する
3. そのまま同じコマンドプロンプトで`cd EasyNovelAssistantosuChitsu/setup && create_uv.bat`を実行する
4. そのまま同じコマンドプロンプトで`cd setup && download_koboldcpp.bat`を実行する  

起動
----
`launch.bat`をクリックして実行  
しばらくすると自動的にブラウザが起動します。

基本的な使い方
--------------
1. 右側の「構成」タブで、タイトル/ジャンル/登場人物/舞台背景などを入力します。
2. 「パラメータ」タブで生成パラメータを調整します。
3. 「KoboldCpp」タブで `koboldcpp.exe` のパスを指定して「起動」します。外部で起動済みの場合は `base_url` を合わせて「起動」します。
4. 「リトライ」を押して生成します。出力は左のテキストボックスに表示されます。

メモ
----
- モデルは `models/llm.json` に定義されています。未ダウンロードの場合は起動時に自動取得します。
- 生成結果は「保存/終了」タブから txt/json で保存できます。

## Lisence

This project is licensed under the MIT License, see the LICENSE.txt file for details