import time
from typing import List, Tuple
import os
import threading
import socket
from backend import KoboldCppBackend,KoboldCppConfig
from gscript_edit import Gscript_editer
import json
import signal
import pathlib
import sys
import random

import gradio as gr



# =========================
# UI helpers (undo/redo)
# =========================

def _push_history(text: str, undo_stack: List[str], redo_stack: List[str]) -> Tuple[List[str], List[str]]:
    # undo_stack は「過去の状態」を積む。redo は新操作が入ったら消す。
    undo_stack = list(undo_stack)
    redo_stack = list(redo_stack)
    undo_stack.append(text)
    redo_stack.clear()
    return undo_stack, redo_stack


def _undo(current: str, undo_stack: List[str], redo_stack: List[str]) -> Tuple[str, List[str], List[str]]:
    undo_stack = list(undo_stack)
    redo_stack = list(redo_stack)

    if not undo_stack:
        return current, undo_stack, redo_stack

    prev = undo_stack.pop()
    redo_stack.append(current)
    return prev, undo_stack, redo_stack


def _redo(current: str, undo_stack: List[str], redo_stack: List[str]) -> Tuple[str, List[str], List[str]]:
    undo_stack = list(undo_stack)
    redo_stack = list(redo_stack)

    if not redo_stack:
        return current, undo_stack, redo_stack

    nxt = redo_stack.pop()
    undo_stack.append(current)
    return nxt, undo_stack, redo_stack


def _build_prompt(title: str, genre: str, characters: str, background: str, additional: str, free_instr: str, current_text: str) -> str:
    """
    UIの各入力から KoboldCpp に渡すプロンプトを作る。
    current_text を渡すことで「続き生成」っぽく動く。
    """
    parts = []
    
    if free_instr.strip():
        parts.append(f"【指示】\n【{free_instr.strip()}】")
    if title.strip():
        parts.append(f"【タイトル】\n【{title.strip()}】")
    if genre.strip():
        parts.append(f"【ジャンル】\n【{genre.strip()}】")  
    if characters.strip():
        parts.append(f"【登場人物】\n{characters.strip()}")  
    if background.strip():
        parts.append(f"【舞台背景】\n{background.strip()}")  
    if current_text.strip():
        parts.append(f"【本文】\n{current_text.strip()}")
    if not current_text.strip():
        parts.append("【本文】\n")
    if additional.strip():
        parts.append(f"【{additional.strip()}】")
    

    #parts.append("【本文】\n")
    return "\n\n".join(parts)


# =========================
# Gradio UI
# =========================

def build_ui() -> gr.Blocks:
    backend = KoboldCppBackend(KoboldCppConfig(base_url="http://127.0.0.1:5001"))
    gse=Gscript_editer()

    with gr.Blocks(title="Easy Novel Assistant osuChitsu") as demo:
        # undo/redo stacks
        undo_stack = gr.State([])  # List[str]
        redo_stack = gr.State([])  # List[str]
        doc_state=gr.State("")
        gscripts_state=gr.State(backend.gscript)
        gsc_edit_state=gr.State({}) #dict
        gsc_edit_state_text=gr.State([]) #List[str]

        with gr.Row():
            gr.Markdown("# Easy Novel Assistant OsuChitsu")

        with gr.Row():
            with gr.Column(scale=2, min_width=480):
                with gr.Row():
                    with gr.Column(scale=2):
                        output_display = gr.Textbox(
                            label="出力表示",
                            lines=35,
                            placeholder="ここに生成された小説が表示されます。",
                            interactive=True,
                            max_lines=35
                        )

                with gr.Row():
                    retry_btn = gr.Button("リトライ",variant="primary")
                    undo_btn = gr.Button("undo")
                    redo_btn = gr.Button("redo")

            with gr.Column(scale=1):
                with gr.Tabs():
                    with gr.TabItem("構成"):
                        with gr.Accordion("文章構成"):                      
                            title = gr.Textbox(label="タイトル", lines=2,max_lines=2)
                            genre = gr.Textbox(label="ジャンル", lines=2,max_lines=2)
                            characters = gr.Textbox(label="登場人物", lines=4,max_lines=4)
                            background=gr.Textbox(label="舞台背景", lines=4,max_lines=4)
                            additional = gr.Textbox(label="続きの展開", lines=4,max_lines=4)
                        with gr.Accordion("その他",open=False):
                            with gr.Column():
                                replace_token=gr.Checkbox(False,label="ガタライズスクリプト")
                                original_gscripts=gr.Checkbox(False,label="オリジナルのガタライズスクリプトを使用")
                            original_file=gr.File(visible="hidden")
                            
                    with gr.TabItem("パラメータ"):
                        temperature = gr.Slider(0.0, 1.0, value=0.7, step=0.05, label="temperature", interactive=True,info="このパラメータが高いほど意外性のある文章になります。")
                        top_k = gr.Slider(1, 64, value=40, step=1, label="top_k", interactive=True,info="このパラメータが高いほどより多様な語彙を使用するようになります。")
                        top_p = gr.Slider(0.01, 1.0, value=0.95, step=0.01, label="top_p", interactive=True,info="このパラメータが高いほどより多様な語彙を使用するようになります。")
                        repeat_penalty = gr.Slider(0, 2.0, value=1.1, step=0.1, label="repeat_penalty", interactive=True, info="このパラメータが高いほど同じ文章の繰り返しを抑制します。")
                        
                        max_new_tokens = gr.Slider(64, 2048, value=512, step=32, label="max_new_tokens", interactive=True,info="1度に生成する文章量を決定します。")
                        

                    with gr.TabItem("KoboldCpp"):
                        
                        if backend.models:
                            model_list=[item for item in backend.models.keys()]
                            model_choice = gr.Dropdown(
                            model_list,
                            label="モデル選択",
                            interactive=True
                        )
                            new_layer= backend.models[model_list[0]]["max_gpu_layer"]
                            layers= gr.Slider(0, new_layer, value=new_layer, step=1, label="layers",info="大きいほどGPUを重点的に使用します。ビデオメモリが小さい場合やCPUで生成したい場合は小さくしてください。")
                            
                        else:
                            model_choice = gr.Dropdown(
                            [],
                            label="モデル選択",
                            interactive=True
                        )
                            layers = gr.Slider(0, 50, value=40, step=1, label="layers",info="大きいほどGPUを重点的に使用します。ビデオメモリが小さい場合やCPUで生成したい場合は小さくしてください。")
                        context_length = gr.Slider(2048, 20480, value=2048, step=2048, label="context_length", interactive=True,info="LLMが参照できる文章量を指定します。長編や設定の細かい作品では大きくしてください。ビデオメモリが小さい場合は小さくしてください。")
                        with gr.Row():
                            start_btn = gr.Button("起動",variant="primary")
                            stop_btn = gr.Button("終了",variant="stop")
                        koboldcpp_exe = gr.Textbox(
                            label="koboldcpp 実行ファイルパス（起動する場合のみ）",
                            placeholder="例: ./koboldcpp  または  C:\\path\\koboldcpp.exe",
                            value="koboldcpp",
                        )
                        base_url = gr.Textbox(label="base_url", value="http://127.0.0.1:5001", interactive=True)
                        status = gr.Markdown("")

                    with gr.TabItem("保存/終了"):
                        extxt=gr.DownloadButton("出力文をtxt保存")
                        exjson=gr.DownloadButton("設定＋出力をjson保存")
                        imjson=gr.Button("設定＋出力をjsonファイルから読み込む")
                        uploadfile=gr.File(visible="hidden",interactive=True)
                        file_status=gr.Markdown("           下の青い文字を押してダウンロードしてください",visible="hidden")
                        downloadfile=gr.File(visible="hidden",interactive=False,show_label=False)                       
                        exit_button=gr.Button("アプリ終了",variant="stop")
                    
                    with gr.TabItem("ガタライズスクリプト作成"):
                        gscfile_edit=gr.File(label="編集したいガタライズスクリプト")
                        gsc_key=gr.Textbox(label="変換したい言葉",info="置き換えたい言葉を入力",placeholder="例: 俺")
                        gsc_value=gr.Textbox(label="変換先の言葉",info="置き換え後の言葉の候補を入力、複数ある場合は「,」で区切る",placeholder="例: 俺は一気に野獣モード,オレ,俺")
                        gsc_add=gr.Button("追加する")
                        gsc_word=gr.Dropdown(label="削除したい語彙")
                        gsc_remove_button=gr.Button("選択した語彙を削除")
                        gsc_save_button=gr.Button("ガタライズスクリプトを保存する")
                        gsc_output_edit=gr.File(label="作成済みファイル",visible="hidden",interactive=False)

                free_instr = gr.Textbox(
                    label="自由指示文",
                    lines=10,
                    placeholder="LLMへの指示を入力",
                    max_lines=10
                )

        # ---- events ----
        def reload_gscripts(path:str):
            backend.reload_gscript(path)
            return backend.gscript
        original_file.upload(reload_gscripts,inputs=[original_file],outputs=[gscripts_state]).then(lambda x:gr.update(visible="hidden"),
                                                                                                inputs=[original_file],outputs=[original_file])

        def switch_bool(bl:bool):
            if bl:
                return gr.update(visible=True)
            else:
                return gr.update(value=None,visible="hidden")
        
        def switch_dict(bl:bool,current:dict):
            if not bl:
                backend.reload_gscript("gscript.json")
                return backend.gscript
            else:
                return current
        original_gscripts.input(switch_bool,inputs=[original_gscripts],outputs=[original_file]).then(switch_dict,inputs=[original_gscripts,gscripts_state],
                                                                                                    outputs=[gscripts_state])

        def save_before(current_text: str):
            if current_text is None or current_text =="":
                return gr.State("")
            return gr.State(current_text)
        output_display.change(save_before,inputs=[output_display],outputs=[doc_state])

        def on_change_base_url(new_url: str):
            backend.config.base_url = new_url
            return f"base_url を {new_url} に設定しました。"

        base_url.change(on_change_base_url, inputs=[base_url], outputs=[status])


        def on_retry_stream(
            current_text: str,
            title: str,
            genre: str,
            characters: str,
            background:str,
            additional:str,
            free_instr: str,
            temperature: float,
            top_k: int,
            top_p: float,
            repeat_penalty: float,
            max_new_tokens: int,
            before: str,
            replace:bool=False,
            replacelist:dict={}
        ):
            # undo 用に、生成前を保存（redoはクリア）
            #undo_stack, redo_stack = _push_history(current_text, undo_stack, redo_stack)
        
            prompt = _build_prompt(title,genre,characters,background, additional, free_instr, current_text)
            params = {
                "temperature": temperature,
                "top_k": top_k,
                "top_p": top_p,
                "repeat_penalty": repeat_penalty,
                "max_new_tokens": max_new_tokens,
            }
        
            base = current_text
            acc = ""  # 生成済みを蓄積
        
            try:
                first=True
                for delta in backend.generate_polled_stream(prompt, params):
                    if first and base != "":
                        first=False
                        continue
                    elif first and before != base and len(base)<1:
                        first=False
                        backend.not_first_gen=True
                        continue
                    acc += delta
                    yield {output_display:base+acc}
            except Exception as e:
                yield acc + f"\n\n[ERROR] streaming failed: {e}\n"
            finally:
                if replace:
                    for item in replacelist.keys():
                        acc=acc.replace(item,random.choice(replacelist[item]))
                    yield {output_display:base+acc}
                else:
                    yield {output_display:base+acc}
        
        

        retry_btn.click(_push_history,inputs=[output_display,undo_stack,redo_stack],outputs=[undo_stack,redo_stack]).then(
            on_retry_stream,
            inputs=[
                output_display,
                characters, title, genre,background,additional, free_instr,
                temperature, top_k, top_p, repeat_penalty, max_new_tokens,
                doc_state,replace_token,gscripts_state
            ],
            outputs=[output_display],
        )

        def on_undo(current_text: str, undo_stack: List[str], redo_stack: List[str]):
            new_text, undo_stack, redo_stack = _undo(current_text, undo_stack, redo_stack)
            return new_text, undo_stack, redo_stack

        def on_redo(current_text: str, undo_stack: List[str], redo_stack: List[str]):
            new_text, undo_stack, redo_stack = _redo(current_text, undo_stack, redo_stack)
            return new_text, undo_stack, redo_stack

        undo_btn.click(on_undo, inputs=[output_display, undo_stack, redo_stack], outputs=[output_display, undo_stack, redo_stack])
        redo_btn.click(on_redo, inputs=[output_display, undo_stack, redo_stack], outputs=[output_display, undo_stack, redo_stack])
        
        def on_download(modelname:str):
            exist,path= backend.check_download(modelname)
            if exist:
                return "ダウンロード済み"
            else:
                check=True
                while check:
                    if os.path.exists(path):
                        check=False
                        yield "ダウンロード済み"
                    else:
                        yield "ダウンロード中"
        
        def on_start(exe: str, model: str, layers: int, base_url: str,context_length: int):
            backend.config.base_url = base_url
            if not exe.strip():
                yield {status:"koboldcpp を外部で起動済みなら exe は空でOKです。base_url だけ合わせてください。"}
            # base_url のポートに合わせたいならここで parse してください（簡易に 5001 固定）
            try:
                port=5001
                if not base_url.endswith("5001"):
                    try:
                        port=int(base_url.split(":")[-1])
                    except Exception:
                        port=5001
                msg = backend.start(exe.strip(), model, layers=layers, port=port,context_length=context_length)
                def is_listening(host: str="127.0.0.1",port: int = port, timeout: float =0.3)-> bool:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(timeout)
                        return s.connect_ex((host, port)) == 0
                deadline=time.time()+300
                while time.time()<deadline:
                    if is_listening():
                        yield "起動完了"
                        break
                    else:
                        yield f"{msg}\n起動中"
                if time.time()>deadline:
                    yield "起動失敗"
            except Exception as e:
                yield {status:f"起動失敗: {e}"}

        def on_stop():
            try:
                return backend.stop()
            except Exception as e:
                return f"終了失敗: {e}"
        
        def load_model_config(modelname):
            new_layer= backend.models[modelname]["max_gpu_layer"]
            return gr.Slider(1, new_layer, value=new_layer, step=1, label="layers",info="大きいほどGPUを重点的に使用します。ビデオメモリが小さい場合やCPUで生成したい場合は小さくしてください。")
        
        def on_exit():
            """
            1) koboldcpp 停止
            2) gradio を閉じる（可能なら）
            3) プロセス強制終了（サーバごと落ちる）
            """
            # 先に koboldcpp を止める（あなたの backend.stop() を使う）
            try:
                backend.stop()
            except Exception:
                pass
            
            # 「UIにメッセージを返す」ために、終了は少し遅らせる
            def _shutdown_later():
                time.sleep(0.3)  # ブラウザへレスポンスを返す猶予
                try:
                    demo.close()   # ポート解放のため（効かない環境もある）
                except Exception:
                    pass
                os._exit(0)       # これが “サーバごと落とす” 本体

            threading.Thread(target=_shutdown_later, daemon=True).start()

            return "アプリを終了しました\nこの画面を閉じてください"
        
        def export_txt(text:str):
            os.makedirs("output",exist_ok=True)
            filename=f"output/{time.strftime('%Y%m%d-%H%M%S')}.txt"
            with open(filename,mode="w",encoding="utf-8")as f:
                text=text
                f.write(text)
            return filename
        
        def export_json(main:str,title:str,genre:str,characters:str,background:str,add:str,free_instr:str,temperature:float,top_k:int,top_p:float,repeat:float,token:int,model:str,layers:int,context:int,undo:list,redo:list):
            os.makedirs("output",exist_ok=True)
            datas={
                "main":main,
                "title":title,
                "genre":genre,
                "characters":characters,
                "background":background,
                "add":add,
                "inst":free_instr,
                "params":{
                    "temp":temperature,
                    "top_k":top_k,
                    "top_p":top_p,
                    "repeat":repeat,
                    "tokens":token
                },
                "koboldcpp":{
                    "modelname":model,
                    "layers":layers,
                    "context":context
                },
                "dolist":{
                    "undo":undo,
                    "redo":redo
                }
            }
            filename=f"output/{time.strftime('%Y%m%d-%H%M%S')}.json"
            with open(filename,mode="w",encoding="utf-8")as f:
                json.dump(datas,f,ensure_ascii=False)
            return filename
        
        def import_json(path:str):
            if os.path.exists(path):
                with open(path,mode="r",encoding="utf-8")as f:
                    datas=json.load(f)
                    param=datas["params"]
                    if "llamacpp" in datas:
                        kobo=datas["llamacpp"]
                    else:
                        kobo=datas["koboldcpp"]
                    dolist=datas["dolist"]
                    return datas["main"],datas["title"],datas["genre"],datas["characters"],datas["background"],datas["add"],datas["inst"],\
                        param["temp"],param["top_k"],param["top_p"],param["repeat"],param["tokens"],kobo["modelname"],kobo["layers"],\
                            kobo["context"],dolist["undo"],dolist["redo"]
            else:
                return "","","","","","","",1.0,40,0.95,1.1,64,"",30,2048,[],[]
        
        ###ガタライズスクリプト作成編集タブ用
        def reload_dropdown(list:list):
            return gr.update(choices=list)
        
        gscfile_edit.upload(
            gse.load_gsc,inputs=[gscfile_edit],outputs=[gsc_edit_state]
            ).then(
            gse.dictkey_to_list,inputs=[],outputs=[gsc_edit_state_text]
            ).then(
            reload_dropdown,inputs=[gsc_edit_state_text],outputs=[gsc_word]
        )
        gsc_remove_button.click(
            gse.remove_from_loaded,inputs=[gsc_word],outputs=[gsc_edit_state_text]
        ).then(
            reload_dropdown,inputs=[gsc_edit_state_text],outputs=[gsc_word]
        )
        gsc_add.click(gse.add_gsc,inputs=[gsc_key,gsc_value],outputs=[gsc_edit_state]).then(
            gse.dictkey_to_list,inputs=[],outputs=[gsc_edit_state_text]
        ).then(
            reload_dropdown,inputs=[gsc_edit_state_text],outputs=[gsc_word]
        ).then(
            lambda x: gr.update(value=""),inputs=[gsc_key],outputs=[gsc_key]
        ).then(
            lambda x: gr.update(value=""),inputs=[gsc_value],outputs=[gsc_value]
        )
        gsc_save_button.click(
            gse.save_to_json,inputs=[],outputs=[gsc_output_edit]
        ).then(
            lambda x:gr.update(visible=True),inputs=[gsc_output_edit],outputs=[gsc_output_edit]
        )
        ###



        start_btn.click(on_download,inputs=[model_choice],outputs=[status]).then(on_start, inputs=[koboldcpp_exe, model_choice, layers, base_url,context_length], outputs=[status])
        stop_btn.click(on_stop, inputs=[], outputs=[status])
        model_choice.change(load_model_config,inputs=[model_choice],outputs=[layers])
        exit_button.click(on_exit,inputs=[],outputs=[output_display])
        extxt.click(export_txt,inputs=[output_display],outputs=[downloadfile]).then(lambda x:gr.update(visible=True),
                                                                        inputs=[file_status],outputs=[file_status]).then(lambda x:gr.update(visible=True),
                                                                                                                        inputs=[downloadfile],outputs=[downloadfile])
        exjson.click(
            export_json,inputs=[output_display,title,genre,characters,background,additional,free_instr,temperature,top_k,top_p,repeat_penalty,max_new_tokens,model_choice,layers,context_length,undo_stack,redo_stack],
                    outputs=[downloadfile]
                    ).then(
                        lambda x:gr.update(visible=True),inputs=[file_status],outputs=[file_status]
                        ).then(
                            lambda x:gr.update(visible=True),inputs=[downloadfile],outputs=[downloadfile])
        imjson.click(lambda x:gr.File(value=None,visible=True),inputs=[uploadfile],outputs=[uploadfile])
        uploadfile.upload(import_json,inputs=[uploadfile],outputs=[output_display,
                    title,genre,characters,background,additional,free_instr,temperature,top_k,top_p,repeat_penalty,max_new_tokens,model_choice,layers,context_length,undo_stack,redo_stack]).\
                        then(lambda x:gr.File(value=None,visible="hidden"),inputs=[uploadfile],outputs=[uploadfile])
        downloadfile.download(lambda x:gr.update(visible="hidden"),inputs=[file_status],outputs=[file_status])

    demo.queue(default_concurrency_limit=1)
    return demo

def cleanup():
    if os.path.exists("output"):
        for file in pathlib.Path("output").iterdir():
            if file.is_file():
                file.unlink()

def signal_handler(signum,frame)->None:
    sys.exit(1)

def main():
    signal.signal(signal.SIGTERM,signal_handler)
    try:
        demo = build_ui()
        demo.launch(inbrowser=True)
    finally:
        cleanup()


if __name__ == "__main__":
    main()
