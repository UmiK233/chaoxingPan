import json
import os
import secrets
import time
import requests
from aes_pkcs5.algorithms.aes_ecb_pkcs5_padding import AESECBPKCS5Padding
from fastapi import FastAPI, Request, Form, UploadFile, File
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response, RedirectResponse
from starlette.templating import Jinja2Templates

# from Crypto.Cipher import AES
# from Crypto.Util.Padding import pad
# import base64


if not os.path.exists('users.json'):
    # 如果文件不存在，创建一个空的JSON文件
    with open('users.json', 'w') as fp:
        json.dump({}, fp, indent=2)


def read_users():
    with open('users.json', 'r') as fp:
        return json.load(fp)


def write_users():
    with open('users.json', 'w') as fp:
        json.dump(users, fp, indent=2)


headers = {
    "User-Agent": "Firefox/89.0"
}

# 模拟数据库
users = dict(read_users())

# 应用实例
app = FastAPI()

templates = Jinja2Templates(directory="templates")

API_BASE_URL = "http://localhost"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def aes_encrypt_pkcs5(key, message):
    cipher = AESECBPKCS5Padding(key, "b64")
    encrypted = cipher.encrypt(message)
    return encrypted


# def aes_encrypt_pkcs7(key, message):
#     # 确保密钥是16、24或32字节长度（对应AES-128/192/256）
#     key_bytes = key.encode('utf-8')
#     message_bytes = message.encode('utf-8')
#
#     # 使用密钥作为IV（初始向量），注意这不是安全做法，仅为兼容原JavaScript代码
#     iv = key_bytes[:16]  # 取密钥的前16字节作为IV
#
#     # 创建AES CBC模式加密器
#     cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
#
#     # 对消息进行PKCS7填充并加密
#     padded_data = pad(message_bytes, AES.block_size)
#     encrypted_bytes = cipher.encrypt(padded_data)
#
#     # 将加密结果转换为Base64字符串
#     return base64.b64encode(encrypted_bytes).decode('utf-8')


def get_headers_uid_token(username, password):
    sess = requests.Session()
    login_key = 'z4ok6lu^oWp4_AES'
    login_message = f'{{"uname":"{username}","code":"{password}"}}'
    login_info = aes_encrypt_pkcs5(login_key, login_message)
    login_url = 'http://passport2-api.chaoxing.com/v11/loginregister'
    login_data = {
        'logininfo': login_info,
        'entype': '1',
    }
    login_res = sess.post(url=login_url, data=login_data, headers=headers, verify=False)
    if login_res.json()["status"] == False:
        return [None, None, None]
    cookies_name = ["fid", "_uid", "_d", "vc3", "uf"]
    cookies = {name: login_res.cookies.get(name) for name in cookies_name}
    cookies_string = '; '.join([f'{k}={v}' for k, v in cookies.items()])

    headers_with_cookies = headers
    headers_with_cookies["Cookie"] = cookies_string

    get_token_url = "http://pan-yz.chaoxing.com/api/token/uservalid"

    get_token_response = requests.get(url=get_token_url, headers=headers)

    token = get_token_response.json()["_token"]

    return [cookies_string, cookies["_uid"], token]


# def get_headers_uid_token(username, password):
#     sess = requests.Session()
#     login_key = 'u2oh6Vu^HWe4_AES'
#     login_url = 'http://passport2.chaoxing.com/fanyalogin'
#     login_data = {
#         'uname': aes_encrypt_pkcs7(login_key, username),
#         'password': aes_encrypt_pkcs7(login_key, password),
#         't': "true"
#     }
#     headers = {
#         "User-Agent": "Firefox/89.0"
#     }
#     login_res = sess.post(url=login_url, data=login_data, headers=headers, verify=False)
#     # print(login_res.cookies)
#     cookies_name = ["fid", "_uid", "_d", "vc3", "uf"]
#     cookies = {name: login_res.cookies.get(name) for name in cookies_name}
#     cookies_string = '; '.join([f'{k}={v}' for k, v in cookies.items()])
#
#     headers_with_cookies = headers
#     headers_with_cookies["Cookie"] = cookies_string
#
#     get_token_url = "http://pan-yz.chaoxing.com/api/token/uservalid"
#
#     get_token_response = requests.get(url=get_token_url, headers=headers)
#
#     token = get_token_response.json()["_token"]
#
#     return [cookies_string, cookies["_uid"], token]


def session_to_curl(url: str, headers: dict, file_name=None):
    command = ["curl"]
    if file_name is not None:
        command = ["curl", "-o", file_name]

    # 添加headers
    for k, v in headers.items():
        command.append(f'-H "{k}: {v}"')

    command.append(f'"{url}"')

    return " ".join(command)


def get_token():
    token = secrets.token_urlsafe(32)
    return token


@app.get("/")
def index(request: Request):
    uid = request.cookies.get('uid')
    user = users.get(uid)
    context = {
        "request": request,
        "API_BASE_URL": API_BASE_URL
    }
    if user is not None:
        return templates.TemplateResponse("index.html", context)
    return RedirectResponse("/loginPage")


@app.get("/loginPage")
def login_page(request: Request):
    uid = request.cookies.get('uid')
    user = users.get(uid)
    if user is not None:
        return RedirectResponse("/")
    context = {
        "request": request,
        "API_BASE_URL": API_BASE_URL
    }
    return templates.TemplateResponse("login.html", context)


@app.post("/login")
async def login(response: Response, username: str = Form(), password: str = Form()):
    xxt_cookies, uid, xxt_token = get_headers_uid_token(username, password)
    # print(xxt_cookies, uid, xxt_token)
    if uid is None:
        return False
    # login_token = get_token()
    users[uid] = {
        "username": username,
        "password": password,
        "xxt_token": xxt_token,
        "xxt_cookies": xxt_cookies,
    }
    response.set_cookie(
        key="uid",
        value=uid,
    )
    write_users()
    return True


@app.get("/logout")
def logout(response: Response, request: Request):
    uid = request.cookies.get('uid')
    if uid is None:
        return "未登录"
    users.pop(uid)
    response.delete_cookie('uid')
    return RedirectResponse("loginPage")


@app.get("/getFiles")
def get_files(request: Request) -> list:
    uid = request.cookies.get('uid')
    if uid is None:
        return ["未登录"]
    user = users[uid]
    xxt_token = user["xxt_token"]
    xxt_cookies = user["xxt_cookies"]
    headers_with_cookies = headers
    headers_with_cookies["Cookie"] = xxt_cookies
    if user is None:
        return ["用户不存在"]
    get_files_url = f"http://pan-yz.chaoxing.com/api/getMyDirAndFiles?puid={uid}&fldid=&page=1&size=100&addrec=0&showCollect=1&_token={xxt_token}"

    # 发送GET请求
    get_files_response = requests.get(url=get_files_url, headers=headers_with_cookies)

    files_list = get_files_response.json()["data"]
    # print(files_list)
    # for i, e in enumerate(files_list):
    #     print(f"文件{i}:{e['name']} resid:{e['resid']} encryptedId:{e['encryptedId']} size:{e['size']}")

    return files_list


@app.get("/getDownload/{res_id}")
def download(request: Request, res_id: str):
    uid = request.cookies.get('uid')
    if uid is None:
        return "未登录"
    user = users.get(uid)
    xxt_token = user["xxt_token"]
    xxt_cookies = user["xxt_cookies"]
    headers_with_cookies = headers
    headers_with_cookies["Cookie"] = xxt_cookies
    if user is None:
        return "用户不存在"
    get_download_url = f"http://pan-yz.chaoxing.com/api/getDownloadUrl?puid={uid}&fleid={res_id}&_token={xxt_token}"

    # 获取下载直链
    get_download_response = requests.get(url=get_download_url, headers=headers_with_cookies)
    # print(get_download_response.text)
    download_url = get_download_response.json()["url"]
    file_name = get_download_response.json()["data"]["name"]

    download_headers = headers
    download_headers["Referer"] = get_download_url

    # download_response = requests.get(url=download_url, headers=download_headers)
    # print(download_response.text)
    return session_to_curl(download_url, download_headers, file_name)


@app.post("/upload")
async def upload_file(request: Request, file: UploadFile = File(...)):
    # print(file)
    file_content = await file.read()
    file_name = file.filename
    uid = request.cookies.get('uid')
    if uid is None:
        return "未登录"
    user = users.get(uid)
    if user is None:
        return "用户不存在"
    xxt_token = user["xxt_token"]
    xxt_cookies = user["xxt_cookies"]
    headers_with_cookies = headers
    headers_with_cookies["Cookie"] = xxt_cookies

    upload_files = [
        ('file', (file_name, file_content, "application/octet-stream"))
    ]
    upload_url = f"http://pan-yz.cldisk.com/upload/uploadfile?_token={xxt_token}&puid={uid}"
    upload_response = requests.post(url=upload_url, headers=headers_with_cookies, files=upload_files)
    # {'code': -6, 'msg': '不能识别的文件类型, 上传失败', 'newCode': 200009, 'result': False}
    # print(upload_response.json())
    if upload_response.json()["result"] == False:
        if upload_response.json()["newCode"] == 200009:
            # 先上传一个正常文件
            modified_file_name = file_name.split(".")[0] + ".txt"
            modified_files = [
                ('file', (modified_file_name, file_content, "application/octet-stream"))
            ]
            modified_upload_response = requests.post(url=upload_url, headers=headers_with_cookies, files=modified_files)
            # print(modified_upload_response.json())
            # 获取他的crc校验码
            crc = modified_upload_response.json()["data"]["crc"]
            file_size = modified_upload_response.json()["data"]["size"]
            # 把上传的替身文件删除
            delete_file(request, modified_upload_response.json()["data"]["resid"])

            newfile_url = f"http://pan-yz.chaoxing.com/api/newfle?_token={xxt_token}"
            newfile_data = {
                "puid": uid,
                "fs": file_size,  # 文件大小
                "fndest": file_name,  # 也是文件名,但是并不决定上传后的文件名称
                "fnorigin": file_name,  # 文件名
                "date": str(int(time.time() * 1000)),
                "crc": crc,
                # "fldid": "0"
            }
            newfile_response = requests.post(url=newfile_url, headers=headers_with_cookies, data=newfile_data)
            # print(newfile_response.json())

            return modified_upload_response.json()["result"]
    return upload_response.json()["result"]


@app.get("/delete/{res_id}")
def delete_file(request: Request, res_id: str):
    uid = request.cookies.get('uid')
    if uid is None:
        return "未登录"
    user = users.get(uid)
    xxt_token = user["xxt_token"]
    xxt_cookies = user["xxt_cookies"]
    headers_with_cookies = headers
    headers_with_cookies["Cookie"] = xxt_cookies
    if user is None:
        return "用户不存在"
    delete_url = f"http://pan-yz.chaoxing.com/api/delete?puid={uid}&resids={res_id}&_token={xxt_token}"
    delete_response = requests.get(url=delete_url, headers=headers_with_cookies)
    # result = delete_response.json()["result"]
    return delete_response.json()


if __name__ == "__main__":
    import uvicorn

    import argparse

    # 创建参数解析器
    parser = argparse.ArgumentParser(description="示例：命令行参数解析")
    # 添加位置参数（必填）
    parser.add_argument("-p", "--port", type=int, default=80, help="端口号（默认80）")
    # 添加可选参数（带默认值和类型）
    parser.add_argument("-u", "--url", type=str, default=API_BASE_URL, help="你的公网地址（如果有）")
    # 添加标志位参数（布尔值）
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细信息")
    # 解析参数
    args = parser.parse_args()

    port = args.port
    API_BASE_URL = f"{args.url}"
    # print(args)
    # print(API_BASE_URL)
    uvicorn.run(app, host="0.0.0.0", port=port)
