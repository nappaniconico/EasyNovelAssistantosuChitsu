pushd %~dp0
pushd ..
python -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
python pip install -r requirements.txt