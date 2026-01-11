from __future__ import annotations

import os
import base64
import hashlib
from dataclasses import dataclass
import json
import time


@dataclass(frozen=True)
class SimpleStringCipher:
    """
    標準ライブラリのみでの簡易暗号(風)。
    - 文字列 -> 暗号文字列(Base64) -> 復号で元に戻せる
    - 強度は“雰囲気”レベル（要件: ぱっと見で読めなければOK向け）

    形式:
        token = base64url( b"SC1" + salt(16) + ciphertext )
    """
    password: str
    iterations: int = 200_000  # PBKDF2の反復回数（少し重くなるが安全側）
    salt_len: int = 16
    header: bytes = b"SC1"     # バージョン識別

    def encrypt(self, plaintext: str) -> str:
        if not isinstance(plaintext, str):
            raise TypeError("plaintext must be str")

        salt = os.urandom(self.salt_len)
        data = plaintext.encode("utf-8")
        key_stream = self._keystream(len(data), salt)

        ct = bytes(b ^ k for b, k in zip(data, key_stream))
        packed = self.header + salt + ct
        return base64.urlsafe_b64encode(packed).decode("ascii")

    def decrypt(self, token: str) -> str:
        if not isinstance(token, str):
            raise TypeError("token must be str")

        try:
            packed = base64.urlsafe_b64decode(token.encode("ascii"))
        except Exception as e:
            raise ValueError("Invalid token (base64 decode failed)") from e

        if len(packed) < len(self.header) + self.salt_len:
            raise ValueError("Invalid token (too short)")

        if packed[: len(self.header)] != self.header:
            raise ValueError("Invalid token (bad header/version)")

        salt = packed[len(self.header) : len(self.header) + self.salt_len]
        ct = packed[len(self.header) + self.salt_len :]

        key_stream = self._keystream(len(ct), salt)
        data = bytes(b ^ k for b, k in zip(ct, key_stream))

        try:
            return data.decode("utf-8")
        except UnicodeDecodeError as e:
            # パスワード違い・破損など
            raise ValueError("Decrypt failed (wrong password or corrupted token)") from e

    def _keystream(self, nbytes: int, salt: bytes) -> bytes:
        """
        PBKDF2で“鍵の元”を作り、カウンタ付きSHA256で必要量まで伸ばす。
        """
        password_bytes = self.password.encode("utf-8")
        seed = hashlib.pbkdf2_hmac("sha256", password_bytes, salt, self.iterations, dklen=32)

        out = bytearray()
        counter = 0
        while len(out) < nbytes:
            counter_bytes = counter.to_bytes(4, "big")
            block = hashlib.sha256(seed + salt + counter_bytes).digest()
            out.extend(block)
            counter += 1

        return bytes(out[:nbytes])
    
    def create_encrypt_json(self,datas:dict,dire="."):
        os.makedirs(dire,exist_ok=True)
        new_datas={}
        for item in datas.keys():
            if isinstance(datas[item],list):
                value=[self.encrypt(it) if isinstance(it,str) else it for it in datas[item] ]
                new_datas.setdefault(item,value)
        filename=f"{dire}/gscript{time.strftime('%Y%m%d-%H%M%S')}.json"
        with open(filename,mode="w",encoding="utf-8")as f:
            json.dump(new_datas,f,ensure_ascii=False)
        return filename
    
    def load_encrypt_json(self,path:str):
        with open(path,mode="r",encoding="utf-8")as f:
            datas=json.load(f)
            new_datas={}
            for item in datas.keys():
                if isinstance(datas[item],list):
                    value=[self.decrypt(it) if isinstance(it,str) else it for it in datas[item]]
                    new_datas.setdefault(item,value)
            return new_datas


if __name__ == "__main__":
    cipher = SimpleStringCipher("my-password")

    s = "こんにちは、これは秘密です！🔒"
    token = cipher.encrypt(s)
    back = cipher.decrypt(token)

    print("token:", token)
    print("back :", back)
    sample={"オレ":["オレは一気に野獣モード"]}
    cipher.create_encrypt_json(sample)
    data=cipher.load_encrypt_json(input("path?"))
    print(data)
