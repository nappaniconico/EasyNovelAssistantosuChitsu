import json
import os
from cipher import SimpleStringCipher

class Gscript_editer:
    def __init__(self):
        self.loaded={}
        self.ssc=SimpleStringCipher("my-password")

    def load_gsc(self,path:str):
        if os.path.exists(path) and path.endswith(".json"):
            self.loaded=self.ssc.load_encrypt_json(path)
            return self.loaded
        else:
            self.loaded={}
            return {}
    
    def add_gsc(self,key:str,values:str):
        if key.strip() and values.strip():
            value_list=values.split(",")
            result=self.loaded.setdefault(key,value_list)
            if result != value_list:
                self.loaded[key]=self.loaded[key]+value_list
            return self.loaded
        else:
            return self.loaded
    
    def dictkey_to_list(self):
        dictkeys=[]
        for item in self.loaded.keys():
            text=f"{item} {self.loaded[item]}"
            dictkeys.append(text)
        return dictkeys
    
    def remove_from_loaded(self,text:str):
        key=text.split()[0]
        self.loaded.pop(key)
        return self.dictkey_to_list()
    
    def save_to_json(self):
        return self.ssc.create_encrypt_json(self.loaded,"output")