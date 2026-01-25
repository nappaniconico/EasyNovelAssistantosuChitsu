import json
import time
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, Optional,  Iterator
import os
import threading
import signal
import requests
import glob
import socket
from cipher import SimpleStringCipher
from chat_template import Chat_templates

# =========================
# KoboldCpp backend class
# =========================

@dataclass
class KoboldCppConfig:
    base_url: str = "http://127.0.0.1:5001"
    timeout_sec: int = 180
    kobold_path="koboldcpp"


class KoboldCppBackend:
    """
    KoboldCpp の HTTP API を叩くバックエンド。
    - generate(prompt, params) で文章生成
    - start/stop は任意（koboldcpp 実行ファイルを持っている場合のみ）
    """

    def __init__(self, config: KoboldCppConfig):
        self.temps=Chat_templates()
        self.config = config
        self._proc: Optional[subprocess.Popen] = None
        self.comp_proc: Optional[subprocess.Popen] = None
        self.not_first_gen=False
        self.ssc=SimpleStringCipher("my-password")
        if os.path.exists("models/llm.json"):
            with open("models/llm.json",mode="r",encoding="utf-8")as f:
                self.models=json.load(f)
                #self.model_list=json.dumps([f'"{item["urls"][0].split("/")[-1:]} : {item["urls"][0]}"' for item in self.models.values()])
            modelfiles=glob.glob("models/*.gguf")
            for key in self.models.keys():
                if "オリジナル" in key:
                    self.models.pop(key)
            for item in modelfiles:
                new_modelname=os.path.basename(item)
                if new_modelname not in [item["urls"][0].split("/")[-1] for item in self.models.values()]:
                    self.models[f"オリジナル/{new_modelname.replace('.gguf','')}"]={"max_gpu_layer":0,"context_size": 4096,"urls":[new_modelname]}
                    #self.model_list=json.dumps([f'"{item["urls"][0].split("/")[-1:]} : {item["urls"][0]}"' for item in self.models.values()]+[])
        else:
            self.models=None

        if os.path.exists("gscript.json"):
            self.gscript=self.ssc.load_encrypt_json("gscript.json")
        else:
            self.gscript={}

    def check_download(self,modelname):
        path=f"models/{os.path.basename(self.models[modelname]['urls'][0])}"
        def downloading(path:str,download_path:str):
            with requests.get(path,stream=True) as r:
                    r.raise_for_status()
                    with open(download_path.replace(".gguf",".part"),"wb") as f:
                        for chunk in r.iter_content(chunk_size=1024*1024):
                            if chunk:
                                f.write(chunk)
                    os.replace(download_path.replace(".gguf",".part"),download_path.replace(".part",".gguf"))
        if os.path.exists(path):
            return True,path
        else:
            threading.Thread(target=downloading,args=(self.models[modelname]['urls'][0],path,),daemon=True).start()
            return False,path
    

    # ---- HTTP helpers ----
    def _post_json(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = self.config.base_url.rstrip("/") + path
        r = requests.post(url, json=payload, timeout=self.config.timeout_sec)
        r.raise_for_status()
        return r.json()
    
    def _get_none(self,path: str):
        url = self.config.base_url.rstrip("/") + path
        r = requests.get(url, timeout=self.config.timeout_sec)
        r.raise_for_status()
        return r.json()

    def _try_generate_endpoints(self, payload: Dict[str, Any]) -> str:
        """
        KoboldCpp は環境によって返却形式が微妙に違うので、代表的な候補を試す。
        """
        candidates = [
            "/api/v1/generate",         # Kobold / KoboldCpp 互換でよく見る
            "/api/v1/generate/text",    # 亜種
            "/api/generate",            # 旧/簡易
        ]

        last_err: Optional[Exception] = None
        for p in candidates:
            try:
                data = self._post_json(p, payload)
                # 返却形式候補を吸収
                # 例1: {"results":[{"text":"..."}]}
                if isinstance(data, dict) and "results" in data and data["results"]:
                    item = data["results"][0]
                    if isinstance(item, dict) and "text" in item:
                        return str(item["text"])

                # 例2: {"text":"..."}
                if isinstance(data, dict) and "text" in data:
                    return str(data["text"])

                # 例3: {"data":{"text":"..."}}
                if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict) and "text" in data["data"]:
                    return str(data["data"]["text"])

                # 形式が想定外ならダンプしてエラー扱い
                raise RuntimeError(f"未知のレスポンス形式: {json.dumps(data, ensure_ascii=False)[:400]}")

            except Exception as e:
                last_err = e

        raise RuntimeError(f"生成APIに接続できませんでした。base_url={self.config.base_url} / err={last_err}")

    # ---- Public API ----
    def generate(self, prompt: str, params: Dict[str, Any]) -> str:
        """
        prompt: 入力プロンプト
        params: temperature, top_k, top_p, repeat_penalty, max_length など
        """
        # Kobold系の一般的な payload 名に寄せる
        payload = {
            "prompt": prompt,
            "temperature": float(params.get("temperature", 0.7)),
            "top_k": int(params.get("top_k", 40)),
            "top_p": float(params.get("top_p", 0.95)),
            "rep_pen": float(params.get("repeat_penalty", 1.1)),
            # Koboldは max_length / max_context_length などが混在しがち
            "max_length": int(params.get("max_new_tokens", 400)),
        }
        return self._try_generate_endpoints(payload)
    
    def _extract_text_from_generate_resp(self, data: dict) -> str:
            if isinstance(data, dict) and "results" in data and data["results"]:
                return str(data["results"][0].get("text", ""))
            if isinstance(data, dict) and "text" in data:
                return str(data["text"])
            if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict) and "text" in data["data"]:
                return str(data["data"]["text"])
            return ""

    def generate_polled_stream(self, prompt: str, params: Dict, header: str="", current_text: str="",cut_mode: str="シンプル",exepath: str="koboldcpp",max_tokens: int=1024) -> Iterator[str]:
        """
        1) 別スレッドで /api/v1/generate を投げて生成開始（ブロッキング回避）
        2) 生成中に /api/extra/generate/check をポーリングして増分を yield
        3) 生成スレッド終了でループ終了（リトライが詰まらない）
        """
        modelname=self._get_none("/api/v1/model")["result"]
        print(modelname)
        template=self.temps.templates["chatml"]
        for temp in self.temps.temp_name.keys():
            if temp in modelname:
                template=self.temps.templates[self.temps.temp_name[temp]]
        
        formated=self.comp_hub(cut_mode,header,current_text,template,exepath,max_tokens)

        
        if self.check_over_tokens(formated)+max_tokens>0:
            yield "Over Max Tokens"

        payload = {
            "prompt": formated,
            "temperature": float(params.get("temperature", 0.7)),
            "top_k": int(params.get("top_k", 40)),
            "top_p": float(params.get("top_p", 0.95)),
            "rep_pen": float(params.get("repeat_penalty", 1.1)),
            "max_length": int(params.get("max_new_tokens", 400)),
        }

        done = {"flag": False}
        final = {"text": "", "err": None}

        def _run_generate():
            try:
                data = self._post_json("/api/v1/generate", payload)
                final["text"] = self._extract_text_from_generate_resp(data)
            except Exception as e:
                final["err"] = e
            finally:
                done["flag"] = True

        t = threading.Thread(target=_run_generate, daemon=True)
        t.start()

        emitted = ""
        idle_count = 0

        while not done["flag"]:
            try:
                chk = self._post_json("/api/extra/generate/check", {})
                cur = ""
                # よくある形式: {"results":[{"text":"..."}]}
                if isinstance(chk, dict) and "results" in chk and chk["results"]:
                    cur = str(chk["results"][0].get("text", "") or "")
                elif isinstance(chk, dict) and "text" in chk:
                    cur = str(chk["text"] or "")

                if cur.startswith(emitted):
                    delta = cur[len(emitted):]
                else:
                    delta = cur  # 形式が変わった/巻き戻った場合は全体出し

                if delta:
                    emitted = cur
                    idle_count = 0
                    yield delta
                else:
                    idle_count += 1

                # check が機能してない環境で永久待ちにならない保険
                if idle_count > 200:  # 0.25秒 * 200 = 約50秒 無変化
                    break

            except Exception:
                # check が無い / 404 / 一時エラーでも、生成スレッドが終われば抜ける
                pass

            time.sleep(0.02)

        # スレッド完了待ち（短く）
        t.join(timeout=0.5)

        if final["err"] is not None:
            raise RuntimeError(str(final["err"]))

        #最後に取りこぼしがあれば吐く
        if final["text"].startswith(emitted):
            tail = final["text"][len(emitted):]
            if tail:
                yield tail
        else:
            # 念のため全出し
            if final["text"]:
                yield final["text"]

        

    def abort(self) -> None:
        """
        生成中断（対応している場合のみ）
        """
        for p in ["/api/v1/abort", "/api/abort"]:
            try:
                self._post_json(p, {})
                return
            except Exception:
                pass

    # ---- Optional: start/stop koboldcpp process ----
    def start(self, koboldcpp_exe: str, model_path: str, layers: int = 40, port: int = 5001,context_length: int = 2048) :
        """
        koboldcpp をプロセス起動したい場合用（任意）。
        koboldcpp_exe: koboldcpp の実行ファイルパス（例: ./koboldcpp.exe や ./koboldcpp）
        model_path: gguf のパス
        """
        if self._proc and self._proc.poll() is None:
            return "すでに起動しています。"

        cmd = [
            koboldcpp_exe,
            "--model", f"models/{self.models[model_path]['urls'][0].split('/')[-1]}",
            "--port", str(port),
            "--gpulayers", str(layers),
            "--contextsize", str(context_length)
        ]
        # 環境によって引数が違うので、必要ならここを調整してください
        self._proc = subprocess.Popen(cmd,
        text=True,
        bufsize=1,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP )
        self.not_first_gen=False

        # 起動待ち（雑に少し待つ）
        return f"起動コマンド: {' '.join(cmd)}"


    def stop(self) -> str:
        if not self._proc:
            return "起動していません。"
        if self._proc.poll() is None:
            self._proc.send_signal(signal.CTRL_BREAK_EVENT)
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
                self._proc.kill()
                print(self._proc.poll())
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None
        return "終了しました。"

    def reload_gscript(self,path: str):
        if os.path.exists(path):
            self.gscript=self.ssc.load_encrypt_json(path)
            return None

#コンテクスト長圧縮用処理
    def setting_aicompresser(self,exepath: str):
        path="models\LFM2.5-1.2B-JP-Q8_0.gguf"
        def downloading(path:str,download_path:str):
            with requests.get(path,stream=True) as r:
                    r.raise_for_status()
                    with open(download_path.replace(".gguf",".part"),"wb") as f:
                        for chunk in r.iter_content(chunk_size=1024*1024):
                            if chunk:
                                f.write(chunk)
                    os.replace(download_path.replace(".gguf",".part"),download_path.replace(".part",".gguf"))
        if os.path.exists(path):
            pass
        else:
            result=threading.Thread(target=downloading,args=("https://huggingface.co/LiquidAI/LFM2.5-1.2B-JP-GGUF/resolve/main/LFM2.5-1.2B-JP-Q8_0.gguf?download=true",path,),daemon=True)
            result.run()
            result.join(timeout=300)
        if self.comp_proc and self.comp_proc.poll() is None:
            return "すでに起動しています。"
        if not os.path.exists(exepath+".exe"):
            return f"{exepath}.exeが見つかりません"

        cmd = [
            exepath,
            "--model", "models\LFM2.5-1.2B-JP-Q8_0.gguf",
            "--port", "5015",
            "--gpulayers", "0",
            "--contextsize", "2048"
        ]
        # 環境によって引数が違うので、必要ならここを調整してください
        self.comp_proc = subprocess.Popen(cmd,
        text=True,
        bufsize=1,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP )
        return "起動完了"
    
    def stop_aicompesser(self):
        if not self.comp_proc:
            return "起動していません。"
        if self.comp_proc.poll() is None:
            self.comp_proc.send_signal(signal.CTRL_BREAK_EVENT)
            self.comp_proc.terminate()
            try:
                self.comp_proc.wait(timeout=5)
                self.comp_proc.kill()
                print(self.comp_proc.poll())
            except subprocess.TimeoutExpired:
                self.comp_proc.kill()
        self.comp_proc = None
        return "終了しました。"
    
    def send_aicompresser(self,text: str):
        """
        prompt: 入力プロンプト
        params: temperature, top_k, top_p, repeat_penalty, max_length など
        """
        # Kobold系の一般的な payload 名に寄せる
        payload = {
            "prompt": "以下の文章を3文以内で要約してください。\n"+text,
            "temperature": 0.7,
            "top_k": 40,
            "top_p": 0.95,
            "rep_pen": 1.1,
            # Koboldは max_length / max_context_length などが混在しがち
            "max_length": 256,
        }

        """
        KoboldCpp は環境によって返却形式が微妙に違うので、代表的な候補を試す。
        """
        candidates = [
            "/api/v1/generate",         # Kobold / KoboldCpp 互換でよく見る
            "/api/v1/generate/text",    # 亜種
            "/api/generate",            # 旧/簡易
        ]

        last_err: Optional[Exception] = None
        for p in candidates:
            try:
                url = "http://127.0.0.1:5015"+p
                r = requests.post(url, json=payload, timeout=self.config.timeout_sec)
                r.raise_for_status()
                data = r.json()
                # 返却形式候補を吸収
                # 例1: {"results":[{"text":"..."}]}
                if isinstance(data, dict) and "results" in data and data["results"]:
                    item = data["results"][0]
                    if isinstance(item, dict) and "text" in item:
                        return str(item["text"])

                # 例2: {"text":"..."}
                if isinstance(data, dict) and "text" in data:
                    return str(data["text"])

                # 例3: {"data":{"text":"..."}}
                if isinstance(data, dict) and "data" in data and isinstance(data["data"], dict) and "text" in data["data"]:
                    return str(data["data"]["text"])

                # 形式が想定外ならダンプしてエラー扱い
                raise RuntimeError(f"未知のレスポンス形式: {json.dumps(data, ensure_ascii=False)[:400]}")

            except Exception as e:
                last_err = e

        raise RuntimeError(f"生成APIに接続できませんでした。base_url={self.config.base_url} / err={last_err}")
    
    def check_over_tokens(self,text: str):
        """
        最大コンテクスト長に対する入力プロンプトの超過量を計算
        
        :param self: 説明
        :param text: 説明
        :type text: str
        """
        token_values=int(self._post_json("/api/extra/tokencount",{"prompt":text})["value"])
        true_max_context_length=int(self._get_none("/api/extra/true_max_context_length")["value"])
        print(f"check current token {token_values}/{true_max_context_length}")
        return token_values-true_max_context_length
    
    def check_current_token(self,text: str):
        return int(self._post_json("/api/extra/tokencount",{"prompt":text})["value"])
    
    def simple_compresser(self,texts:list[str], header: str, template: str, max_tokens: int):
        over=True
        formated=template.format(header + "\n".join(texts))
        over_length=self.check_over_tokens(formated)+max_tokens
        current_length=self.check_current_token("\n".join(texts))
        first_sentence=int(len(texts)*over_length/current_length)
        while over:
            new_texts=texts[first_sentence:]
            if self.check_over_tokens(template.format(header + "\n".join(new_texts)))+max_tokens<0:
                over=False
            else:
                first_sentence+=1
        return "\n".join(new_texts)
    
    def ai_compresser(self,texts:list[str], header: str, template: str, max_tokens: int):
        n = 20
        chunks = [texts[i:i + n] for i in range(0, len(texts), n)]
        if self.comp_proc and self.comp_proc.poll() is None:
            pass
        else:
            print(self.setting_aicompresser(exepath=self.config.kobold_path))
            def is_listening(host: str="127.0.0.1",port: int = 5015, timeout: float =0.3)-> bool:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(timeout)
                        return s.connect_ex((host, port)) == 0
            while not is_listening():
                time.sleep(0.1)
        over=True
        current_index=0
        comped_chunks=[]
        while over:
            comped_chunks.append(self.send_aicompresser("\n".join(chunks[current_index])))
            new_raw_text=""
            for item in comped_chunks:
                new_raw_text+=item
            for item in chunks[len(comped_chunks):]:
                new_raw_text+="\n".join(item)
            new_texts=template.format(header + new_raw_text)
            length=self.check_over_tokens(new_texts)
            if length+max_tokens<0:
                over=False
            current_index+=1
        return new_raw_text
    
    def comp_hub(self,mode: str,header: str, current_text:str, template: str,exepath: str, max_tokens: int):  
        formatted=template.format(header+current_text)
        if self.check_over_tokens(formatted)+max_tokens<0:
            return formatted
        texts=current_text.split("\n")
        print(mode)
        mode_dict={
            "シンプル":1,
            "AI圧縮":2
        }
        match mode_dict[mode]:
            case 1:
                print(1)
                self.stop_aicompesser()
                result=self.simple_compresser(texts,header,template,max_tokens)
            case 2:
                print(2)
                result=self.ai_compresser(texts,header,template,max_tokens)
            case _:
                result=""
                print(3)
        print(result)
        return template.format(header+result)